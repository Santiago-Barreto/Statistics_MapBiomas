"""
Módulo de Gestión de Assets - MapBiomas Colombia
Utiliza la base de datos local para alimentar la interfaz de usuario
"""

import ee
from data.db import (
    listar_assets_bioma_db,
    listar_versiones_region_db,
    obtener_biomas_db,
    obtener_regiones_por_bioma_db,
)

def obtener_biomas():
    """
    Retorna los biomas únicos registrados en la base de datos local.
    """
    return obtener_biomas_db()

def regiones_por_bioma(bioma_nombre):
    """
    Retorna las regiones asociadas a un bioma específico desde la base de datos local.
    """
    return obtener_regiones_por_bioma_db(bioma_nombre)

def listar_versiones_disponibles(region_id):
    """
    Consulta las versiones de assets disponibles para una región en la base de datos.
    """
    return listar_versiones_region_db(str(region_id))


def listar_assets_por_bioma(bioma_nombre):
    """
    Retorna todos los assets asociados al bioma seleccionado.
    """
    return listar_assets_bioma_db(bioma_nombre)

def leer_stats_procesadas(asset_id):
    """
    Extrae datos crudos de GEE. Solo es llamada por el motor de sincronización.
    """
    try:
        fc = ee.FeatureCollection(asset_id)
        data = fc.getInfo()
        return [f['properties'] for f in data.get('features', [])]
    except Exception as e:
        print(f"Error leyendo asset en GEE: {e}")
        return []