"""
Módulo Principal - MapBiomas Dashboard Colombia
Orquestador de la aplicación que integra la inicialización de servicios,
sincronización de base de datos y renderizado de componentes.
"""

import streamlit as st
from gee.init import inicializar_gee
from data.db import inicializar_db
from sync.manager import chequeo_automatico_sincro
from data.processing import cargar_datos_totales
from ui.sidebar import render_sidebar
from ui.components import render_header_metrics
from ui.map import render_visual_inspector
from ui.charts import render_dashboard_view, render_graphs_only_view, render_combined_view

def main():
    """
    Controla el ciclo de vida de la aplicación, asegurando la persistencia
    local y la actualización de estadísticas mediante procesos internos.
    """
    st.set_page_config(
        page_title="MapBiomas Dashboard", 
        layout="wide", 
        page_icon="🌱"
    )

    inicializar_db()
    inicializar_gee()
    chequeo_automatico_sincro()
    
    if "thumbnails" not in st.session_state:
        st.session_state.thumbnails = None

    region_id, version_sel, modo_vista = render_sidebar()

    st.title("🌱 Estadísticas MapBiomas Colombia: C4")
    
    if not version_sel:
        st.info("💡 Selecciona versiones en el panel lateral para comenzar el análisis.")
        st.stop()

    with st.spinner("⏳ Cargando datos locales..."):
        data_dict = cargar_datos_totales(version_sel)

    if not data_dict:
        st.error("Error: No se encontraron datos para la selección.")
        st.stop()

    render_header_metrics(region_id, data_dict)
    render_visual_inspector(region_id, version_sel, data_dict)

    st.divider()

    vistas = {
        "Dashboard Completo": render_dashboard_view,
        "Solo Gráficas": render_graphs_only_view,
        "Comparativa Combinada": render_combined_view
    }
    
    render_func = vistas.get(modo_vista)
    if render_func:
        render_func(data_dict, region_id)

if __name__ == "__main__":
    main()