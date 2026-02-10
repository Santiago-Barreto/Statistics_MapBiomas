"""
Módulo Principal - MapBiomas Dashboard Colombia
Aplicación Streamlit para la visualización de estadísticas 
y comparación de clasificaciones de cobertura, tanto filtros como clasificación base.
"""

import streamlit as st
from gee.init import inicializar_gee
from data.processing import cargar_datos_totales
from ui.sidebar import render_sidebar
from ui.components import render_header_metrics
from ui.map import render_visual_inspector
from ui.charts import render_dashboard_view, render_graphs_only_view, render_combined_view


def main():
    """
    Controla el flujo de ejecución de la plataforma:
    1. Inicializa servicios (GEE).
    2. Gestiona el estado de la sesión.
    3. Renderiza componentes de UI y lógica de visualización.
    """
    
    st.set_page_config(
        page_title="MapBiomas Dashboard", 
        layout="wide", 
        page_icon="🌱"
    )
    inicializar_gee()

    if "thumbnails" not in st.session_state:
        st.session_state.thumbnails = None

    region_id, version_sel, modo_vista = render_sidebar()

    st.title("🌱 Estadísticas MapBiomas Colombia: C4")
    
    if not version_sel:
        st.info("💡 Selecciona versiones en el panel lateral.")
        st.stop()

    with st.spinner("⏳ Procesando estadísticas..."):
        data_dict = cargar_datos_totales(version_sel)

    if not data_dict:
        st.error("Error al procesar datos.")
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