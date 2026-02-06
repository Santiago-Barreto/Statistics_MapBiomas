"""
Módulo de Componentes de Interfaz - MapBiomas Colombia
Define elementos visuales reutilizables para la identidad y el resumen 
estadístico del dashboard.
"""

import streamlit as st

def render_header_metrics(region_id, data_dict):
    """
    Renderiza la sección de encabezado con métricas de resumen ejecutivo.

    Args:
        region_id (str): Identificador único de la región geográfica.
        data_dict (dict): Diccionario que contiene los DataFrames procesados por versión.
    """
    primer_df = next(iter(data_dict.values()))
    
    st.markdown(f"### 📊 Reporte: Región {region_id}")
    
    col_reg, col_ver, col_per = st.columns(3)
    
    col_reg.metric(
        label="Región", 
        value=region_id
    )
    col_ver.metric(
        label="Versiones activas", 
        value=len(data_dict)
    )
    col_per.metric(
        label="Periodo", 
        value=f"{primer_df['year'].min()} - {primer_df['year'].max()}"
    )
    
    st.divider()