"""
Módulo de Sincronización Automática - MapBiomas Colombia
Gestiona la actualización de datos locales y el registro de nuevos 
descubrimientos de assets en la infraestructura de GEE.
"""

import time
import ee
from data.db import (
    DB_OPERATIONAL_ERRORS,
    get_conn,
    insert_assets_upsert_sql,
    insert_stats_upsert_sql,
    ph,
    ph_join,
    upsert_control_sincro_sql,
)
from data.year_norm import normalize_year
from gee.assets import leer_stats_procesadas
from config import ASSET_PARENT, ASSET_REGIONES


def hay_assets_sin_stats():
    """True si existen assets en la BD sin ninguna fila en stats."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1 FROM assets a
        WHERE NOT EXISTS (SELECT 1 FROM stats s WHERE s.asset_id = a.asset_id)
        LIMIT 1
        """
    )
    existe = cur.fetchone() is not None
    conn.close()
    return existe


def rellenar_stats_faltantes_desde_gee(asset_ids=None):
    """
    Descarga estadísticas desde GEE para assets que existen localmente pero
    tienen tabla stats vacía (p. ej. fallo anterior de red o sincro saltada por el cronómetro).
    Si asset_ids se informa, solo considera ese subconjunto.
    Devuelve True si el commit en la base de datos fue exitoso.
    """
    conn = get_conn()
    cur = conn.cursor()

    try:
        if asset_ids:
            placeholders = ph_join(len(asset_ids))
            cur.execute(
                f"""
                SELECT DISTINCT a.asset_id FROM assets a
                WHERE NOT EXISTS (
                    SELECT 1 FROM stats s WHERE s.asset_id = a.asset_id
                )
                AND a.asset_id IN ({placeholders})
                """,
                list(asset_ids),
            )
        else:
            cur.execute(
                """
                SELECT a.asset_id FROM assets a
                WHERE NOT EXISTS (
                    SELECT 1 FROM stats s WHERE s.asset_id = a.asset_id
                )
                """
            )

        pendientes = [row[0] for row in cur.fetchall()]

        for a_id in pendientes:
            raw_data = leer_stats_procesadas(a_id)
            if not raw_data:
                continue

            rows_cob = _construir_rows_stats(a_id, raw_data)
            if rows_cob:
                cur.executemany(insert_stats_upsert_sql(), rows_cob)

        conn.commit()
        return True
    except DB_OPERATIONAL_ERRORS:
        conn.rollback()
        return False
    finally:
        conn.close()


def _construir_rows_stats(asset_id, raw_data):
    """
    Convierte propiedades crudas de GEE en filas para la tabla stats.
    """
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

            rows_cob.append((asset_id, year, k_norm.split('_')[0], value))

    return rows_cob


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
        total, nombres, ok = sincronizar_todo_interno()
        if ok:
            for intento in range(3):
                conn = None
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute(upsert_control_sincro_sql(), (ahora, total, nombres))
                    conn.commit()
                    break
                except DB_OPERATIONAL_ERRORS as exc:
                    if "locked" not in str(exc).lower() or intento == 2:
                        break
                    time.sleep(0.5 * (intento + 1))
                finally:
                    if conn is not None:
                        conn.close()

    # Aunque el cronómetro de sync no permita lista remota nueva, los assets
    # locales pueden seguir sin stats (GEE falló antes o BD heredada). Rellenar siempre el hueco.
    if hay_assets_sin_stats():
        rellenar_stats_faltantes_desde_gee()

def sincronizar_todo_interno():
    """
    Compara el inventario local con Google Earth Engine para coberturas, descarga estadísticas para nuevos assets y 
    retorna un resumen de los cambios realizados.

    Las llamadas a GEE se hacen SIN mantener abierta la conexión SQLite (evita database is locked).
    """
    try:
        remote_assets_cob = ee.data.listAssets({"parent": ASSET_PARENT}).get("assets", [])
    except Exception:
        return 0, "", False

    remote_ids_cob = {a.get("id") for a in remote_assets_cob if a.get("id")}

    try:
        bioma_mapping_raw = ee.FeatureCollection(ASSET_REGIONES).reduceColumns(
            ee.Reducer.toList().repeat(2), ["id_regionC", "bioma"]
        ).getInfo()
    except Exception:
        bioma_mapping_raw = {"list": [[], []]}

    listas = bioma_mapping_raw.get("list", [[], []])
    bioma_dict = dict(zip([str(x) for x in listas[0]], listas[1]))

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT asset_id FROM assets")
        local_ids_cob = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT DISTINCT asset_id FROM stats")
        stats_ids = {r[0] for r in cur.fetchall()}
    except Exception:
        if conn is not None:
            conn.close()
        return 0, "", False
    finally:
        if conn is not None:
            conn.close()
            conn = None

    if not remote_ids_cob and local_ids_cob:
        return 0, "", False

    new_assets_cob = remote_ids_cob - local_ids_cob
    assets_sin_stats = (remote_ids_cob & local_ids_cob) - stats_ids
    nombres_nuevos = [nid.split("/")[-1] for nid in new_assets_cob]

    # Descargar stats desde GEE fuera de la transacción SQLite.
    stats_por_asset: dict[str, list] = {}
    for a_id in new_assets_cob | assets_sin_stats:
        raw_data = leer_stats_procesadas(a_id)
        if raw_data:
            stats_por_asset[a_id] = raw_data

    filas_assets = []
    ahora = int(time.time())
    for asset in remote_assets_cob:
        a_id = asset.get("id")
        if not a_id:
            continue
        label = a_id.split("/")[-1]
        label_norm = label.replace("-", "_")
        region_id = label_norm.split("_V")[0].replace("R", "")
        bioma = bioma_dict.get(region_id, "Sin Bioma")
        filas_assets.append((a_id, region_id, bioma, label, ahora))

    def _escribir():
        c = get_conn()
        try:
            cur = c.cursor()
            cur.executemany(insert_assets_upsert_sql(), filas_assets)
            for a_id, raw_data in stats_por_asset.items():
                rows_cob = _construir_rows_stats(a_id, raw_data)
                if rows_cob:
                    cur.executemany(insert_stats_upsert_sql(), rows_cob)
            c.commit()
            return True
        except DB_OPERATIONAL_ERRORS:
            c.rollback()
            return False
        finally:
            c.close()

    from data.db import with_sqlite_retry

    try:
        ok = with_sqlite_retry(_escribir)
    except DB_OPERATIONAL_ERRORS:
        return 0, "", False

    if not ok:
        return 0, "", False
    return len(nombres_nuevos), ", ".join(nombres_nuevos), True


def _prefijo_stats() -> str:
    return ASSET_PARENT.rstrip("/") + "/"


def purgar_assets_fuera_de_parent() -> int:
    """
    Elimina de la BD local assets/stats que no pertenecen a ASSET_PARENT
    (p. ej. copias en ee-my-andesnorte / STATISTICS_GENERAL).
    """
    prefijo = _prefijo_stats()

    def _borrar():
        c = get_conn()
        try:
            cur = c.cursor()
            cur.execute(
                f"SELECT asset_id FROM assets WHERE asset_id NOT LIKE {ph()}",
                (f"{prefijo}%",),
            )
            ajenos = [r[0] for r in cur.fetchall()]
            if not ajenos:
                return 0
            phs = ph_join(len(ajenos))
            cur.execute(f"DELETE FROM stats WHERE asset_id IN ({phs})", ajenos)
            cur.execute(f"DELETE FROM assets WHERE asset_id IN ({phs})", ajenos)
            c.commit()
            return len(ajenos)
        except DB_OPERATIONAL_ERRORS:
            c.rollback()
            return -1
        finally:
            c.close()

    from data.db import with_sqlite_retry

    try:
        return with_sqlite_retry(_borrar)
    except DB_OPERATIONAL_ERRORS:
        return -1


def reexportar_todas_estadisticas():
    """
    Re-descarga desde GEE todas las estadísticas de ASSET_PARENT y
    sobrescribe la tabla stats local. No usa otros proyectos.

    Returns
    -------
    dict con keys: ok, n_assets, n_con_stats, n_fallidos, n_purgados, detalle_fallidos
    """
    resultado = {
        "ok": False,
        "n_assets": 0,
        "n_con_stats": 0,
        "n_fallidos": 0,
        "n_purgados": 0,
        "detalle_fallidos": [],
    }

    n_purgados = purgar_assets_fuera_de_parent()
    if n_purgados < 0:
        return resultado
    resultado["n_purgados"] = n_purgados

    try:
        remote_assets = ee.data.listAssets({"parent": ASSET_PARENT}).get("assets", [])
    except Exception:
        return resultado

    remote_ids = [a.get("id") for a in remote_assets if a.get("id")]
    resultado["n_assets"] = len(remote_ids)
    if not remote_ids:
        resultado["ok"] = True
        return resultado

    try:
        bioma_mapping_raw = ee.FeatureCollection(ASSET_REGIONES).reduceColumns(
            ee.Reducer.toList().repeat(2), ["id_regionC", "bioma"]
        ).getInfo()
    except Exception:
        bioma_mapping_raw = {"list": [[], []]}

    listas = bioma_mapping_raw.get("list", [[], []])
    bioma_dict = dict(zip([str(x) for x in listas[0]], listas[1]))

    stats_por_asset: dict[str, list] = {}
    fallidos: list[str] = []
    for a_id in remote_ids:
        raw = leer_stats_procesadas(a_id)
        if raw:
            stats_por_asset[a_id] = raw
        else:
            fallidos.append(a_id.rsplit("/", 1)[-1])

    ahora = int(time.time())
    filas_assets = []
    for a_id in remote_ids:
        label = a_id.split("/")[-1]
        label_norm = label.replace("-", "_")
        region_id = label_norm.split("_V")[0].replace("R", "")
        bioma = bioma_dict.get(region_id, "Sin Bioma")
        filas_assets.append((a_id, region_id, bioma, label, ahora))

    def _escribir():
        c = get_conn()
        try:
            cur = c.cursor()
            cur.executemany(insert_assets_upsert_sql(), filas_assets)
            for a_id, raw_data in stats_por_asset.items():
                # Reemplazar stats del asset (reexport limpio)
                cur.execute(f"DELETE FROM stats WHERE asset_id = {ph()}", (a_id,))
                rows_cob = _construir_rows_stats(a_id, raw_data)
                if rows_cob:
                    cur.executemany(insert_stats_upsert_sql(), rows_cob)
            c.commit()
            return True
        except DB_OPERATIONAL_ERRORS:
            c.rollback()
            return False
        finally:
            c.close()

    from data.db import with_sqlite_retry

    try:
        ok = with_sqlite_retry(_escribir)
    except DB_OPERATIONAL_ERRORS:
        return resultado

    resultado["ok"] = bool(ok)
    resultado["n_con_stats"] = len(stats_por_asset)
    resultado["n_fallidos"] = len(fallidos)
    resultado["detalle_fallidos"] = fallidos[:30]
    return resultado
