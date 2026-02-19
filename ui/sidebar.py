"""
Módulo de Interfaz Lateral - MapBiomas Colombia
Renderiza la configuración, el registro de sincronización y herramientas de validación externa.
"""

import streamlit as st
import datetime
import re
from gee.assets import obtener_biomas, regiones_por_bioma, listar_versiones_disponibles
from sync.manager import obtener_resumen_sincro
from ui.formatters import formatear_nombre_humano, categorizar_versiones, organizar_reporte_novedades
from config import MODOS_APP
from gee.assets_agricultura import (
    listar_assets_agricultura
)


def render_sidebar():
    """
    Renderiza los controles de navegación y herramientas adicionales en la barra lateral.
    """
    region_id = None
    version_sel = []
    modo_vista = None
    modo = 0

    with st.sidebar:
    
        modo_label = st.segmented_control(
            "Modo",
            options=list(MODOS_APP.keys()),
            selection_mode="single",
            default=list(MODOS_APP.keys())[0],
            label_visibility="collapsed"
        )

        modo = MODOS_APP[modo_label]

        if modo == list(MODOS_APP.values())[0]:
            st.divider()
            biomas = obtener_biomas()
            bioma_sel = st.selectbox("🌎 Bioma", biomas)
            regiones = regiones_por_bioma(bioma_sel)
            region_id = st.selectbox("📍 Región", regiones)

            versiones_raw = listar_versiones_disponibles(region_id)
            if not versiones_raw: 
                st.stop()

            st.subheader("Selección de Versiones")
            categorias = categorizar_versiones(versiones_raw)
            version_sel = []

            for cat, assets in categorias.items():
                if assets:
                    st.markdown(f"**{cat}**")
                    for item in assets:
                        if st.checkbox(formatear_nombre_humano(item), key=item):
                            version_sel.append(item)
            
            st.divider()
            modo_vista = st.radio("Visualización", ["Dashboard Completo", "Solo Gráficas", "Comparativa Combinada"])
            
            st.divider()

            st.subheader("Comparación en GEE")
            st.info("Compara los resultados de la Colección 4 frente a la Colección 3 en el visor oficial (También puedes ver los limites entre regiones y biomas ;D)")
            
            st.link_button(
                "🔍 Visor Comparativo C3 vs C4",
                "https://mapbiomas-andesnorte.users.earthengine.app/view/coleccion4",
                width='content',
                help="Accede a la App de GEE para validación cruzada entre colecciones."
            )

        elif modo == list(MODOS_APP.values())[1]:
            st.divider()

            assets_filtrado_agricultura = listar_assets_agricultura()

            if not assets_filtrado_agricultura:
                st.warning("No hay estadísticas de agricultura disponibles.")
                st.stop()

            region_agri = st.selectbox(
            "🌎 Región agricultura",
            assets_filtrado_agricultura,
            format_func=lambda x: re.search(r'_R(\d+)$', x).group(1) if re.search(r'_R(\d+)$', x) else x
            )

            match = re.search(r'_R(\d+)$', region_agri)
            region_id = int(match.group(1)) if match else None
            version_sel = [region_agri]

            st.divider()

            modo_vista = st.radio(
                "Visualización",
                ["Dashboard Completo", "Solo Gráficas"]
            )
        st.divider()


        

    return region_id, version_sel, modo_vista, modo
