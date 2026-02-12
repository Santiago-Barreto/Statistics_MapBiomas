"""
Módulo Principal - MapBiomas Dashboard Colombia

Orquesta la inicialización de servicios,
sincronización automática y renderizado
de los componentes principales de la aplicación.
"""

import streamlit as st

from gee.init import inicializar_gee
from data.db import inicializar_db
from sync.manager import chequeo_automatico_sincro
from data.processing import cargar_datos_totales

from ui.sidebar import render_sidebar
from ui.components import render_header_metrics
from ui.map import render_visual_inspector
from ui.charts import (
    render_dashboard_view,
    render_graphs_only_view,
    render_combined_view
)


# ---------------------------------------------------------------------
# Configuración e Inicialización
# ---------------------------------------------------------------------

def configurar_app():
    st.set_page_config(
        page_title="MapBiomas Dashboard",
        layout="wide",
        page_icon="🌱"
    )


def inicializar_servicios():
    inicializar_db()
    inicializar_gee()
    chequeo_automatico_sincro()


def inicializar_estado():
    if "thumbnails" not in st.session_state:
        st.session_state.thumbnails = None


# ---------------------------------------------------------------------
# Aplicación Principal
# ---------------------------------------------------------------------

def main():
    configurar_app()
    inicializar_servicios()
    inicializar_estado()

    region_id, version_sel, modo_vista = render_sidebar()

    # Header institucional
    st.markdown("""
        <div style='padding: 0.5rem 0 1.5rem 0;'>
            <h1 style='margin-bottom:0;'>Estadísticas MapBiomas Colombia</h1>
            <p style='color:gray; margin-top:0;'>
                Colección 4 · Panel Analítico Regional
            </p>
        </div>
    """, unsafe_allow_html=True)

    if not version_sel:
        st.info("Selecciona versiones en el panel lateral para iniciar el análisis.")
        st.stop()

    with st.spinner("Cargando datos locales..."):
        data_dict = cargar_datos_totales(version_sel)

    if not data_dict:
        st.error("No se encontraron datos para la selección realizada.")
        st.stop()

    # Componentes principales
    render_header_metrics(region_id, data_dict)
    render_visual_inspector(region_id, version_sel, data_dict)

    st.divider()

    vistas = {
        "Dashboard Completo": render_dashboard_view,
        "Solo Gráficas": render_graphs_only_view,
        "Comparativa Combinada": render_combined_view
    }

    vistas[modo_vista](data_dict, region_id)


# ---------------------------------------------------------------------

if __name__ == "__main__":
    main()
