"""
Módulo Principal - MapBiomas Dashboard Colombia

Orquesta la inicialización de servicios, sincronización automática 
y renderizado de los componentes principales de la aplicación.
"""

import streamlit as st
from config import MODOS_APP
from data.db import inicializar_db
from gee.init import inicializar_gee
from sync.manager import chequeo_automatico_sincro
from data.processing import cargar_datos_totales, cargar_datos_agricultura
from ui.sidebar import render_sidebar
from ui.map import render_visual_inspector
from ui.status import render_status_popover 
from ui.admin import render_admin_zone     
from ui.charts import (
    render_dashboard_view,
    render_graphs_only_view,
    render_combined_view
)
from ui.charts_agricultura import render_metrics_agricultura, plot_temporal_series_agricultura

def configurar_app():
    """
    Define la configuración técnica de la página y estilos CSS base.
    """
    st.set_page_config(
        page_title="MapBiomas Dashboard",
        layout="wide",
        page_icon="🌱",
        initial_sidebar_state="expanded"
    )
    st.markdown("""
        <style>
            .main-header { padding: 0rem 0 0.5rem 0; }
            .stApp [data-testid="stToolbar"] { display: none; }
            /* Alineación del botón de Info a la derecha */
            [data-testid="stPopover"] {
                text-align: right;
            }
        </style>
    """, unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def iniciar_servicios_una_vez():
    """
    Inicializa las conexiones persistentes de base de datos y Google Earth Engine.
    """
    inicializar_db()
    inicializar_gee()
    return True

def procesar_sincronizacion():
    """
    Gestiona el flujo de sincronización automática una vez por sesión de usuario.
    """
    if "ultima_sincro" not in st.session_state:
        chequeo_automatico_sincro()
        st.session_state.ultima_sincro = True

@st.dialog("⚙️ ASSETS Y GEE", width="large")
def mostrar_admin_dialog(modo, region_id):
    """
    Ventana modal para administración y estado.
    """
    render_status_popover()
    st.divider()
    render_admin_zone(modo, region_id) 

def main():
    """
    Punto de entrada principal que coordina el flujo de datos y la interfaz.
    """
    configurar_app()
    iniciar_servicios_una_vez()
    procesar_sincronizacion()

    if "thumbnails" not in st.session_state:
        st.session_state.thumbnails = None

    region_id, version_sel, modo_vista, modo = render_sidebar()

    if "modo_anterior" not in st.session_state:
        st.session_state.modo_anterior = modo

    if st.session_state.modo_anterior != modo:
        st.session_state.modo_anterior = modo
        st.session_state.thumbnails = None

    col_title, col_info = st.columns([0.85, 0.15])

    with col_info:
        if st.button("⚙️ INFORMACIÓN", use_container_width=True, help="Estado y Gestión"):
            mostrar_admin_dialog(modo, region_id)

    with col_title:
        if modo == list(MODOS_APP.values())[0]:
            st.markdown(f"""
                <div class='main-header'>
                    <h1 style='margin-bottom:0;'>Estadísticas MapBiomas Colombia - Coberturas</h1>
                    <p style='color:gray; margin-top:0;'>Colección 4 · Región {region_id} · Panel Analítico</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class='main-header'>
                    <h1 style='margin-bottom:0;'>Estadísticas MapBiomas Colombia - Transversal Agricultura</h1>
                    <p style='color:gray; margin-top:0;'>Colección 4 · Región {region_id} · Panel Analítico</p>
                </div>
            """, unsafe_allow_html=True)

    if modo == list(MODOS_APP.values())[0]:
        if not version_sel:
            st.info("💡 Selecciona versiones en el panel lateral para iniciar el análisis.")
            st.stop()

        with st.spinner("Cargando datos..."):
            data_dict = cargar_datos_totales(version_sel)

        if not data_dict:
            st.error("No se encontraron datos para la selección realizada.")
            st.stop()

        render_visual_inspector(region_id, version_sel, data_dict)
        st.divider()

        vistas = {
            "Dashboard Completo": render_dashboard_view,
            "Solo Gráficas": render_graphs_only_view,
            "Comparativa Combinada": render_combined_view
        }

        if modo_vista in vistas:
            vistas[modo_vista](data_dict, region_id)

    elif modo == list(MODOS_APP.values())[1]:
        if not version_sel:
            st.info("💡 Selecciona una región de agricultura en el panel lateral.")
            st.stop()

        df_agri = cargar_datos_agricultura(version_sel)        
        if df_agri is None:
            st.error("No se encontraron datos de agricultura para la región seleccionada.")
            st.stop()

        st.subheader("📊 Agricultura - Serie Completa")
        render_metrics_agricultura(df_agri)
        plot_temporal_series_agricultura(df_agri, region_id)

if __name__ == "__main__":
    main()