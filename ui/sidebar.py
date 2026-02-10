"""
Módulo de Interfaz Lateral (Sidebar) - MapBiomas Colombia
Gestiona la captura de parámetros del usuario, permitiendo filtrar regiones,
seleccionar versiones de clasificación y definir el modo de visualización.
"""

import streamlit as st
from gee.assets import obtener_biomas, regiones_por_bioma, listar_versiones_disponibles
from data.processing import extraer_label_version

def render_sidebar():
    """
    Renderiza los widgets de control en la barra lateral de Streamlit.

    Returns:
        tuple: Contiene (region_id, version_sel, modo) seleccionados por el usuario.
    """
    with st.sidebar:
        st.header("Configuración")
        

        biomas = obtener_biomas()
        bioma_sel = st.selectbox("Seleccionar Bioma", biomas)
        regiones = regiones_por_bioma(bioma_sel)
        
        
        if not regiones:
            st.error(f"No hay regiones para el bioma {bioma_sel}.")
            st.stop()

        region_id = st.selectbox("Seleccionar Región", regiones)
        
        versiones = listar_versiones_disponibles(region_id)
        
        if not versiones:
            st.warning(f"Sin versiones para {region_id}")
            st.stop()

        version_sel = st.multiselect(
                    label="Versiones a comparar", 
                    options=versiones, 
                    default=versiones[:1],
                    format_func=extraer_label_version
                )
        
        st.divider()
        
        modo = st.radio(
            label="Modo de visualización", 
            options=["Dashboard Completo", "Solo Gráficas", "Comparativa Combinada"]
        )
        st.divider()

        if st.button("🔄 Actualizar Datos GEE", use_container_width=True):
            st.cache_data.clear()
            st.toast("Actualizando datos desde GEE… las nuevas versiones aparecerán pronto.", icon="🛰️")
        
        
    return region_id, version_sel, modo