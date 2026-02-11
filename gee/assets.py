"""
Módulo de Gestión de Assets - MapBiomas Colombia
Proporciona herramientas para interactuar con la infraestructura de datos de 
Google Earth Engine, incluyendo el descubrimiento de regiones y versiones.
"""

import ee
import os
import re
from config import ASSET_PARENT , ASSET_REGIONES
import streamlit as st

@st.cache_data(show_spinner=False)
def obtener_biomas():
    """
    Retorna la lista de biomas únicos disponibles en el asset de regiones.
    """
    regiones_fc = ee.FeatureCollection(ASSET_REGIONES)
    return regiones_fc.aggregate_array("bioma").distinct().sort().getInfo()

@st.cache_data(show_spinner=False)
def regiones_por_bioma(bioma_nombre):
    """
    Filtra y retorna los IDs de las regiones que pertenecen a un bioma.
    """
    regiones_fc = ee.FeatureCollection(ASSET_REGIONES)
    filtro = regiones_fc.filter(ee.Filter.eq("bioma", bioma_nombre))
    return filtro.aggregate_array("id_regionC").sort().getInfo()

@st.cache_data(show_spinner=False, ttl=300)
def listar_versiones_disponibles(region_id):
    """
    Escanea el repositorio de GEE buscando assets que coincidan con el ID 
    de la región, soportando formatos con prefijo 'R' o 'COLOMBIA-'.

    Args:
        region_id (str/int): Identificador de la región (ej. '30205' o 'R30205').

    Returns:
        list: Lista de rutas completas de los assets de estadísticas encontrados.
    """
    clean_id = re.sub(r"\D", "", str(region_id))
    
    try:
        folder_content = ee.data.listAssets({'parent': ASSET_PARENT})
        assets = folder_content.get('assets', [])

        pattern = re.compile(f"R{clean_id}|-{clean_id}")    

        match = [
            a['id'] for a in assets 
            if pattern.search(a['id'])
        ]
        
        return sorted(match, reverse=True)
    
    except Exception as e:
        st.error(f"Error al listar assets en GEE: {e}")
        return []
    
@st.cache_data(show_spinner=False)
def leer_stats_procesadas(asset_id):
    """
    nombre_asset ya contiene la ruta completa (ej. projects/mapbiomas.../R30205-V1)
    """
    try:
        fc = ee.FeatureCollection(asset_id)
        data = fc.getInfo()
        
        return [f['properties'] for f in data.get('features', [])]
    except Exception as e:
        print(f"Error leyendo asset: {e}")
        return []
