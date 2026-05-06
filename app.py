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
from data.processing import cargar_datos_totales, cargar_datos_bioma
from ui.sidebar import render_sidebar
from ui.map import render_visual_inspector
from ui.status import render_status_popover 
from ui.admin import render_admin_zone     
from ui.charts import (
    render_dashboard_view,
    render_graphs_only_view,
    render_combined_view,
)

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
            /* No ocultar la barra superior completa: ahí está el control para reabrir el sidebar. */
            [data-testid="stDeployButton"] { display: none !important; }
            [data-testid="stToolbar"] [data-testid="stToolbarActions"] {
                gap: 0.25rem;
            }
            .main .block-container {
                padding-left: clamp(0.75rem, 2vw, 2rem);
                padding-right: clamp(0.75rem, 2vw, 2rem);
                padding-top: clamp(0.5rem, 1.5vw, 1.25rem);
                max-width: min(1600px, 100vw);
            }
            .main-header {
                padding: 0rem 0 0.5rem 0;
                animation: fadeIn 0.5s ease-in-out;
            }
            .main-header.dashboard-card h1 {
                font-size: clamp(1.15rem, 1.25rem + 1.2vw, 1.75rem);
                line-height: 1.25;
            }
            .main-header.dashboard-card p {
                font-size: clamp(0.8rem, 0.75rem + 0.35vw, 0.95rem);
            }
            [data-testid="stPopover"] {
                text-align: right;
            }
            .dashboard-card {
                border: 1px solid rgba(151, 166, 195, 0.25);
                border-radius: 14px;
                padding: clamp(0.5rem, 1.2vw, 0.85rem) clamp(0.65rem, 2vw, 1rem);
                background: linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,248,252,0.78));
                box-shadow: 0 8px 20px rgba(21, 34, 50, 0.06);
                margin-bottom: 0.6rem;
                min-width: 0;
                box-sizing: border-box;
            }
            div[data-testid="stHorizontalBlock"]:has(div[data-testid="column"]:has(div.main-header.dashboard-card)) {
                align-items: flex-start !important;
            }
            @media (max-width: 900px) {
                section.main div[data-testid="stHorizontalBlock"]:has(.dashboard-card) {
                    flex-wrap: wrap !important;
                    row-gap: 0.65rem !important;
                }
                section.main div[data-testid="stHorizontalBlock"]:has(.dashboard-card) > div[data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 0 !important;
                }
            }
            .js-plotly-plot, .plotly {
                width: 100% !important;
                max-width: 100%;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(6px); }
                to { opacity: 1; transform: translateY(0px); }
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
def mostrar_admin_dialog(modo, region_id, bioma_sel=None):
    """
    Ventana modal para administración y estado.
    """
    render_status_popover()
    st.divider()
    render_admin_zone(modo, region_id, bioma_sel=bioma_sel)

def main():
    """
    Punto de entrada principal que coordina el flujo de datos y la interfaz.
    """
    configurar_app()
    iniciar_servicios_una_vez()
    procesar_sincronizacion()

    if "thumbnails" not in st.session_state:
        st.session_state.thumbnails = None

    region_id, version_sel, modo_vista, modo, scope, bioma_sel = render_sidebar()

    if "modo_anterior" not in st.session_state:
        st.session_state.modo_anterior = modo

    if st.session_state.modo_anterior != modo:
        st.session_state.modo_anterior = modo
        st.session_state.thumbnails = None

    col_title, col_info = st.columns([0.85, 0.15])

    with col_info:
        if st.button("⚙️ INFORMACIÓN", use_container_width=True, help="Estado y Gestión"):
            mostrar_admin_dialog(
                modo,
                region_id,
                bioma_sel=bioma_sel if scope == "bioma" else None,
            )

    with col_title:
        alcance_txt = f"Bioma {bioma_sel}" if scope == "bioma" else f"Región {region_id}"
        st.markdown(f"""
            <div class='main-header dashboard-card'>
                <h1 style='margin-bottom:0;'>Estadísticas MapBiomas Colombia - Coberturas</h1>
                <p style='color:gray; margin-top:0;'>Colección 4 · {alcance_txt} · Panel Analítico</p>
            </div>
        """, unsafe_allow_html=True)

    if modo == list(MODOS_APP.values())[0]:
        if scope == "region" and not version_sel:
            st.info("💡 Selecciona versiones en el panel lateral para iniciar el análisis.")
            st.stop()

        with st.spinner("Cargando datos..."):
            if scope == "bioma":
                data_dict = cargar_datos_bioma(version_sel, bioma_sel)
            else:
                data_dict = cargar_datos_totales(version_sel)

        if not data_dict:
            st.error("No se encontraron datos para la selección realizada.")
            st.stop()

        if scope == "region":
            render_visual_inspector(region_id, version_sel, data_dict)
            st.divider()

        vistas = {
            "Dashboard Completo": render_dashboard_view,
            "Solo Gráficas": render_graphs_only_view,
            "Comparativa Combinada": render_combined_view
        }

        if modo_vista in vistas:
            chart_scope = bioma_sel if scope == "bioma" else region_id
            vistas[modo_vista](data_dict, chart_scope)

if __name__ == "__main__":
    main()
