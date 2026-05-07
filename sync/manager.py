"""
Módulo de Sincronización Automática - MapBiomas Colombia
Gestiona la actualización de datos locales y el registro de nuevos 
descubrimientos de assets en la infraestructura de GEE.
"""

import time
import ee
import re
import uuid
from data.db import (
    borrar_assets_db,
    borrar_stats_agri_db,
    borrar_stats_db,
    guardar_resumen_sincro_db,
    listar_assets_agri_locales_db,
    listar_assets_cob_locales_db,
    obtener_resumen_sincro_db,
    release_sync_lock,
    try_acquire_sync_lock,
    upsert_assets_db,
    upsert_stats_agri_db,
    upsert_stats_db,
)
from data.year_norm import normalize_year
from gee.assets import leer_stats_procesadas
from config import ASSET_PARENT, ASSET_REGIONES, ASSET_PARENT_AGRICULTURA


def obtener_resumen_sincro():
    """
    Recupera los metadatos del último proceso de sincronización, 
    incluyendo fecha, cantidad de novedades y etiquetas.
    """
    return obtener_resumen_sincro_db()

def chequeo_automatico_sincro():
    """
    Determina la necesidad de sincronización basada en el tiempo transcurrido 
    y actualiza el registro de control tras completar el proceso.
    """
    res_sincro = obtener_resumen_sincro()
    ultima_fecha = res_sincro[0]
    ahora = int(time.time())
    
    if ultima_fecha and (ahora - ultima_fecha) <= 600:
        return

    owner_id = str(uuid.uuid4())
    if not try_acquire_sync_lock(owner_id, ttl_seconds=120):
        return

    try:
        # Doble chequeo dentro del lock para evitar trabajo redundante.
        ultima_fecha_locked, _, _ = obtener_resumen_sincro_db()
        ahora_locked = int(time.time())
        if ultima_fecha_locked and (ahora_locked - ultima_fecha_locked) <= 600:
            return

        total, nombres = sincronizar_todo_interno()
        guardar_resumen_sincro_db(ahora_locked, total, nombres)
    finally:
        release_sync_lock(owner_id)

def sincronizar_todo_interno():
    """
    Compara el inventario local con Google Earth Engine para los módulos de 
    Coberturas y Agricultura, descarga estadísticas para nuevos assets y 
    retorna un resumen de los cambios realizados.
    """
    try:
        remote_assets_cob = ee.data.listAssets({'parent': ASSET_PARENT}).get('assets', [])
        remote_assets_agri = ee.data.listAssets({'parent': ASSET_PARENT_AGRICULTURA}).get('assets', [])
    except Exception:
        return 0, ""

    remote_ids_cob = {a.get('id') for a in remote_assets_cob if a.get('id')}
    remote_ids_agri = {a.get('id') for a in remote_assets_agri if a.get('id')}

    try:
        bioma_mapping_raw = ee.FeatureCollection(ASSET_REGIONES).reduceColumns(
            ee.Reducer.toList().repeat(2), ['id_regionC', 'bioma']
        ).getInfo()
    except Exception:
        bioma_mapping_raw = {'list': [[], []]}

    listas = bioma_mapping_raw.get('list', [[], []])
    bioma_dict = dict(zip([str(x) for x in listas[0]], listas[1]))

    local_ids_cob = listar_assets_cob_locales_db()
    local_ids_agri = listar_assets_agri_locales_db()

    new_assets_cob = remote_ids_cob - local_ids_cob
    new_assets_agri = remote_ids_agri - local_ids_agri

    nombres_nuevos = (
        [nid.split('/')[-1] for nid in new_assets_cob] +
        [nid.split('/')[-1] for nid in new_assets_agri]
    )

    for d_id in (local_ids_cob - remote_ids_cob):
        borrar_stats_db([d_id])
        borrar_assets_db([d_id])

    for d_id in (local_ids_agri - remote_ids_agri):
        borrar_stats_agri_db([d_id])

    rows_assets = []
    rows_cob = []
    for asset in remote_assets_cob:
        a_id = asset.get('id')
        if not a_id:
            continue
        label = a_id.split('/')[-1]
        label_norm = label.replace('-', '_')
        region_id = label_norm.split('_V')[0].replace('R', '')
        bioma = bioma_dict.get(region_id, "Sin Bioma")

        rows_assets.append(
            {
                "asset_id": a_id,
                "region_id": region_id,
                "bioma": bioma,
                "label": label,
                "last_sync": int(time.time()),
            }
        )

        if a_id in new_assets_cob:
            raw_data = leer_stats_procesadas(a_id)

            if raw_data:
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

                        rows_cob.append(
                            {
                                "asset_id": a_id,
                                "year": year,
                                "class_id": k_norm.split('_')[0],
                                "area_ha": value,
                            }
                        )

    rows_agri = []
    for asset in remote_assets_agri:
        a_id = asset.get('id')
        if not a_id:
            continue
        label = a_id.split('/')[-1]

        if not re.search(r'^STATS_TRANSVERSAL_AGRICULTURA', label):
            continue

        if a_id in new_assets_agri:
            raw_data = leer_stats_procesadas(a_id)

            if raw_data:
                for r in raw_data:
                    year = normalize_year(r.get('year'))
                    if year is None:
                        continue

                    for k, v in r.items():
                        if k in ['year', 'version', 'system:index']:
                            continue

                        try:
                            value = float(v)
                        except (ValueError, TypeError):
                            continue

                        rows_agri.append(
                            {
                                "asset_id": a_id,
                                "year": year,
                                "metric": k,
                                "value": value,
                            }
                        )

    upsert_assets_db(rows_assets)
    upsert_stats_db(rows_cob)
    upsert_stats_agri_db(rows_agri)

    return len(nombres_nuevos), ", ".join(nombres_nuevos)
