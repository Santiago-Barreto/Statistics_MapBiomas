"""
Módulo de Gestión de Assets - MapBiomas Colombia
Utiliza la base de datos local para alimentar la interfaz de usuario
"""

import ee
import re
import streamlit as st
from data.db import get_conn, ph

def obtener_biomas():
    """
    Retorna los biomas únicos registrados en la base de datos local.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT bioma FROM assets WHERE bioma IS NOT NULL ORDER BY bioma ASC")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def regiones_por_bioma(bioma_nombre):
    """
    Retorna las regiones asociadas a un bioma específico desde la base de datos local.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"SELECT DISTINCT region_id FROM assets WHERE bioma = {ph()} ORDER BY region_id ASC",
        (bioma_nombre,),
    )
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def listar_versiones_disponibles(region_id):
    """
    Consulta las versiones de assets disponibles para una región en la base de datos.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"SELECT asset_id FROM assets WHERE region_id = {ph()} ORDER BY asset_id DESC",
        (str(region_id),),
    )
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def listar_assets_por_bioma(bioma_nombre):
    """
    Retorna todos los assets asociados al bioma seleccionado.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"SELECT asset_id FROM assets WHERE bioma = {ph()} ORDER BY asset_id DESC",
        (bioma_nombre,),
    )
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

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