"""
Módulo de Sincronización Automática - MapBiomas Colombia
Gestiona la actualización de datos locales y el registro de nuevos 
descubrimientos de assets en la infraestructura de GEE.
"""

import time
import ee
import sqlite3
from data.db import get_conn
from data.year_norm import normalize_year
from gee.assets import leer_stats_procesadas
from config import ASSET_PARENT, ASSET_REGIONES


def obtener_resumen_sincro():
    """
    Recupera los metadatos del último proceso de sincronización, 
    incluyendo fecha, cantidad de novedades y etiquetas.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT ultima_fecha, total_nuevos, nombres_nuevos FROM control_sincro WHERE id = 1")
    res = cur.fetchone()
    conn.close()
    return res if res else (None, 0, "")

def chequeo_automatico_sincro():
    """
    Determina la necesidad de sincronización basada en el tiempo transcurrido 
    y actualiza el registro de control tras completar el proceso.
    """
    res_sincro = obtener_resumen_sincro()
    ultima_fecha = res_sincro[0]
    ahora = int(time.time())
    
    if not ultima_fecha or (ahora - ultima_fecha) > 600:
        total, nombres = sincronizar_todo_interno()
        for intento in range(3):
            conn = None
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR REPLACE INTO control_sincro (id, ultima_fecha, total_nuevos, nombres_nuevos) 
                    VALUES (1, ?, ?, ?)
                """, (ahora, total, nombres))
                conn.commit()
                break
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower() or intento == 2:
                    break
                time.sleep(0.5 * (intento + 1))
            finally:
                if conn is not None:
                    conn.close()

def sincronizar_todo_interno():
    """
    Compara el inventario local con Google Earth Engine para coberturas, descarga estadísticas para nuevos assets y 
    retorna un resumen de los cambios realizados.
    """
    conn = None

    try:
        conn = get_conn()
        cur = conn.cursor()
        remote_assets_cob = ee.data.listAssets({'parent': ASSET_PARENT}).get('assets', [])
    except Exception:
        if conn is not None:
            conn.close()
        return 0, ""

    remote_ids_cob = {a.get('id') for a in remote_assets_cob if a.get('id')}

    try:
        bioma_mapping_raw = ee.FeatureCollection(ASSET_REGIONES).reduceColumns(
            ee.Reducer.toList().repeat(2), ['id_regionC', 'bioma']
        ).getInfo()
    except Exception:
        bioma_mapping_raw = {'list': [[], []]}

    listas = bioma_mapping_raw.get('list', [[], []])
    bioma_dict = dict(zip([str(x) for x in listas[0]], listas[1]))

    cur.execute("SELECT asset_id FROM assets")
    local_ids_cob = {r[0] for r in cur.fetchall()}

    new_assets_cob = remote_ids_cob - local_ids_cob

    nombres_nuevos = [nid.split('/')[-1] for nid in new_assets_cob]

    for d_id in (local_ids_cob - remote_ids_cob):
        cur.execute("DELETE FROM assets WHERE asset_id = ?", (d_id,))
        cur.execute("DELETE FROM stats WHERE asset_id = ?", (d_id,))

    for asset in remote_assets_cob:
        a_id = asset.get('id')
        if not a_id:
            continue
        label = a_id.split('/')[-1]
        label_norm = label.replace('-', '_')
        region_id = label_norm.split('_V')[0].replace('R', '')
        bioma = bioma_dict.get(region_id, "Sin Bioma")

        cur.execute(
            "INSERT OR REPLACE INTO assets VALUES (?, ?, ?, ?, ?)",
            (a_id, region_id, bioma, label, int(time.time()))
        )

        if a_id in new_assets_cob:
            raw_data = leer_stats_procesadas(a_id)

            if raw_data:
                rows_cob = []

                for r in raw_data:
                    year = normalize_year(r.get('year'))
                    if year is None:
                        continue

                    for k, v in r.items():
                        k_norm = k.replace('-', '_')

                        if k_norm in ['year', 'version', 'system:index', 'clase_transversal', 'regionId']:
                            continue

                        try:
                            value = float(v)
                        except (ValueError, TypeError):
                            continue

                        rows_cob.append((a_id, year, k_norm.split('_')[0], value))

                if rows_cob:
                    cur.executemany(
                        "INSERT OR REPLACE INTO stats VALUES (?, ?, ?, ?)",
                        rows_cob
                    )

    try:
        conn.commit()
    except sqlite3.OperationalError:
        conn.rollback()
        return 0, ""
    finally:
        conn.close()

    return len(nombres_nuevos), ", ".join(nombres_nuevos)
