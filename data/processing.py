"""
Módulo de Procesamiento de Datos - MapBiomas Colombia
Transforma datos provenientes de la base de datos local o Google Earth Engine 
en estructuras de Pandas DataFrame optimizadas para análisis y visualización.
"""

import pandas as pd
from data.db import get_conn
from data.year_norm import normalize_year


def _to_int_year(value):
    return normalize_year(value)

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
    query = f"""
        SELECT asset_id, year, class_id, area_ha
        FROM stats 
        WHERE asset_id IN ({placeholders})
        ORDER BY asset_id, year
    """
    
    df_raw = pd.read_sql(query, conn, params=asset_ids)
    conn.close()

    if df_raw.empty:
        return {}

    data_dict = {}

    df_raw["year"] = df_raw["year"].apply(_to_int_year)
    df_raw = df_raw.dropna(subset=["year"])
    df_raw["year"] = df_raw["year"].astype("int32")

    for a_id, df_v in df_raw.groupby("asset_id"):
        label = extraer_label_version(a_id)

        df_pivot = (
            df_v
            .pivot(index='year', columns='class_id', values='area_ha')
            .reset_index()
        )

        df_pivot["version"] = label
        data_dict[label] = df_pivot

    return data_dict


def cargar_datos_bioma(asset_ids, biome_name):
    """
    Agrega estadísticas de múltiples assets (regiones) para un bioma completo.
    """
    if not asset_ids:
        return {}

    conn = get_conn()
    placeholders = ",".join(["?"] * len(asset_ids))
    query = f"""
        SELECT year, class_id, SUM(area_ha) AS area_ha
        FROM stats
        WHERE asset_id IN ({placeholders})
        GROUP BY year, class_id
        ORDER BY year
    """
    df_raw = pd.read_sql(query, conn, params=asset_ids)
    conn.close()

    if df_raw.empty:
        return {}

    df_raw["year"] = df_raw["year"].apply(_to_int_year)
    df_raw = df_raw.dropna(subset=["year"])
    if df_raw.empty:
        return {}

    df_raw["year"] = df_raw["year"].astype("int32")

    df_pivot = (
        df_raw
        .pivot(index="year", columns="class_id", values="area_ha")
        .reset_index()
        .sort_values("year")
    )
    df_pivot["version"] = f"BIOMA_{biome_name}".upper().replace(" ", "_")

    return {f"Bioma {biome_name}": df_pivot}


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

    nuevas_columnas = {
        col: col.split('_', 1)[0]
        for col in df.columns
        if col not in ['year', 'version']
    }

    df = df.rename(columns=nuevas_columnas)

    df['year'] = df['year'].astype('int16')
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
    return path.rsplit('/', 1)[-1]

def cargar_datos_agricultura(asset_ids):
    """
    Carga datos agrícolas unificados directamente desde SQL.
    Retorna un único DataFrame con una columna 'version' normalizada.
    """
    if not asset_ids:
        return None

    conn = get_conn()
    placeholders = ','.join(['?'] * len(asset_ids))
    query = f"""
        SELECT asset_id, year, metric, value
        FROM stats_agricultura
        WHERE asset_id IN ({placeholders})
          AND metric NOT IN ('regionId', 'clase_transversal')
        ORDER BY year ASC
    """
    df = pd.read_sql(query, conn, params=asset_ids)
    conn.close()

    if df.empty:
        return None

    df['version'] = df['asset_id'].str.rsplit('/', n=1).str[-1]
    
    df = df.drop(columns=['asset_id'])

    return df