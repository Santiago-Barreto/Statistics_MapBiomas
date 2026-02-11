"""
Módulo de Procesamiento de Datos - MapBiomas Colombia
Transforma datos provenientes de la base de datos local o Google Earth Engine 
en estructuras de Pandas DataFrame optimizadas para análisis y visualización.
"""

import pandas as pd
from data.db import get_conn

def cargar_datos_totales(asset_ids):
    """
    Consulta la base de datos local para extraer estadísticas de área asociadas 
    a los identificadores de asset proporcionados y retorna un diccionario 
    de DataFrames estructurados.
    """
    if not asset_ids:
        return {}
    
    conn = get_conn()
    placeholders = ','.join(['?'] * len(asset_ids))
    query = f"SELECT asset_id, year, class_id, area_ha FROM stats WHERE asset_id IN ({placeholders})"
    
    df_raw = pd.read_sql(query, conn, params=asset_ids)
    conn.close()

    if df_raw.empty:
        return {}

    data_dict = {}
    for a_id in asset_ids:
        label = extraer_label_version(a_id)
        df_v = df_raw[df_raw['asset_id'] == a_id].copy()
        
        if not df_v.empty:
            df_pivot = df_v.pivot(index='year', columns='class_id', values='area_ha').reset_index()
            df_pivot['version'] = label
            data_dict[label] = df_pivot

    return data_dict

def construir_dataframe(raw_data, version):
    """
    Transforma una lista de diccionarios con metadatos de GEE en un 
    DataFrame de Pandas con limpieza de columnas de sistema y normalización 
    de identificadores de clase.
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
    Realiza la concatenación de múltiples estructuras DataFrame en una única 
    tabla unificada para procesos de comparación multiversión.
    """
    return pd.concat(dfs, ignore_index=True, sort=False) if dfs else None

def extraer_label_version(path):
    """
    Extrae y normaliza la etiqueta final del asset a partir de su ruta 
    completa en Google Earth Engine.
    """
    return path.split('/')[-1]