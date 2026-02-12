"""
Módulo de Sincronización Automática - MapBiomas Colombia
Gestiona la actualización de datos locales y el registro de nuevos 
descubrimientos de assets en la infraestructura de GEE.
"""

import time
import ee
from data.db import get_conn
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
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO control_sincro (id, ultima_fecha, total_nuevos, nombres_nuevos) 
            VALUES (1, ?, ?, ?)
        """, (ahora, total, nombres))
        conn.commit()
        conn.close()

def sincronizar_todo_interno():
    """
    Compara el inventario local con GEE, descarga estadísticas para nuevos 
    identificadores y retorna un resumen de los cambios realizados.
    """
    conn = get_conn()
    cur = conn.cursor()
    
    remote_assets = ee.data.listAssets({'parent': ASSET_PARENT}).get('assets', [])
    remote_ids = {a['id'] for a in remote_assets}

    bioma_mapping_raw = ee.FeatureCollection(ASSET_REGIONES).reduceColumns(
        ee.Reducer.toList().repeat(2), ['id_regionC', 'bioma']
    ).getInfo()
    listas = bioma_mapping_raw.get('list', [[], []])
    bioma_dict = dict(zip([str(x) for x in listas[0]], listas[1]))

    cur.execute("SELECT asset_id FROM assets")
    local_ids = {r[0] for r in cur.fetchall()}
    
    new_assets = remote_ids - local_ids
    nombres_nuevos = [nid.split('/')[-1] for nid in new_assets]
    
    for d_id in (local_ids - remote_ids):
        cur.execute("DELETE FROM assets WHERE asset_id = ?", (d_id,))
        cur.execute("DELETE FROM stats WHERE asset_id = ?", (d_id,))

    for asset in remote_assets:
        a_id = asset['id']
        label = a_id.split('/')[-1]
        label_norm = label.replace('-', '_')
        region_id = label_norm.split('_V')[0].replace('R', '')
        bioma = bioma_dict.get(region_id, "Sin Bioma")
        
        cur.execute("INSERT OR REPLACE INTO assets VALUES (?, ?, ?, ?, ?)", 
                    (a_id, region_id, bioma, label, int(time.time())))
        
        if a_id in new_assets:
            raw_data = leer_stats_procesadas(a_id)
            if raw_data:
                rows = []
                for r in raw_data:
                    year = int(r.get('year', 0))
                    for k, v in r.items():
                        k_norm = k.replace('-', '_')
                        if k_norm not in ['year', 'version', 'system:index']:
                            try:
                                rows.append((a_id, year, k_norm.split('_')[0], float(v)))
                            except (ValueError, TypeError):
                                continue
                
                if rows:
                    cur.executemany("INSERT OR REPLACE INTO stats VALUES (?, ?, ?, ?)", rows)
    
    conn.commit()
    conn.close()
    return len(nombres_nuevos), ", ".join(nombres_nuevos)