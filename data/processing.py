"""
Módulo de Procesamiento de Datos - MapBiomas Colombia
Transforma datos crudos provenientes de Google Earth Engine en estructuras
de Pandas DataFrame optimizadas para análisis y visualización.
"""

import pandas as pd
import streamlit as st
from gee.assets import leer_stats_procesadas

@st.cache_data(show_spinner=False)
def cargar_datos_totales(seleccion):
    """
    Carga y transforma múltiples assets de GEE.
        Args:
        region (str): Identificador de la región.
        seleccion (list): Lista de rutas de assets seleccionados.
            Returns:
        dict: Diccionario de DataFrames indexados por el nombre de la versión.
    """
    data = {}

    for v_asset in seleccion:
        raw = leer_stats_procesadas(v_asset)
        label = extraer_label_version(v_asset)      
        df = construir_dataframe(raw, label)

        if df is not None and not df.empty:
            data[label] = df

    return data

def construir_dataframe(raw_data, version):
    """
    Convierte una lista de diccionarios (GEE) en un DataFrame limpio.
    Args:
        raw_data (list): Datos crudos obtenidos de la API de GEE.
        version (str): Etiqueta de la versión para identificar los datos. 
    Returns:
        pandas.DataFrame: DataFrame procesado o None si no hay datos.
    """
    if not raw_data:
        return None
        
    df = pd.DataFrame(raw_data)
    
    cols_drop = {'system:index', 'geo'}
    df = df.drop(columns=[c for c in cols_drop if c in df.columns])
    
    nuevas_columnas = {}
    for col in df.columns:
        if col not in ['year', 'version']:
            nuevas_columnas[col] = col.split('_')[0]
            
    df = df.rename(columns=nuevas_columnas)
    
    df['year'] = df['year'].astype(int)
    df['version'] = version
    
    return df

def fusionar_versiones(dfs):
    """
    Concatena una lista de DataFrames en una única estructura tabular.
    
    Args:
        dfs (list): Lista de pandas.DataFrames.
        
    Returns:
        pandas.DataFrame: Estructura unificada o None.
    """
    return pd.concat(dfs, ignore_index=True, sort=False) if dfs else None

def extraer_label_version(path):
    """
    Función centralizada para limpiar nombres de assets de GEE.
    Convierte 'projects/.../R30205-V11_stats' en 'R30205-V11'.
    """
    return path.split('/')[-1]


