"""
Módulo de Interfaz Lateral - MapBiomas Colombia
Renderiza la configuración, el registro de sincronización y herramientas de validación externa.
"""

import streamlit as st
from gee.assets import (
    obtener_biomas,
    regiones_por_bioma,
    listar_versiones_disponibles,
    listar_assets_por_bioma,
)
from ui.formatters import (
    formatear_nombre_humano,
    categorizar_versiones,
    seleccionar_assets_base_ultima_version_efectiva,
)
from config import MODOS_APP


def render_sidebar():
    """
    Renderiza los controles de navegación y herramientas adicionales en la barra lateral.
    """
    region_id = None
    version_sel = []
    modo_vista = None
    modo = list(MODOS_APP.values())[0]
    scope = "region"
    bioma_sel = None

    with st.sidebar:
    
        _modo_keys = list(MODOS_APP.keys())
        if len(_modo_keys) == 1:
            modo_label = _modo_keys[0]
            st.markdown("**🎯 Coberturas**")
        else:
            modo_label = st.segmented_control(
                "Modo",
                options=_modo_keys,
                selection_mode="single",
                default=_modo_keys[0],
                label_visibility="collapsed",
            )
            if modo_label is None:
                modo_label = _modo_keys[0]

        modo = MODOS_APP[modo_label]

        if modo == list(MODOS_APP.values())[0]:
            st.divider()
            biomas = obtener_biomas()
            bioma_sel = st.selectbox("🌎 Bioma", biomas)

            alcance = st.radio(
                "Alcance",
                ["Región", "Bioma completo"],
                horizontal=True
            )
            scope = "region" if alcance == "Región" else "bioma"

            if scope == "region":
                regiones = regiones_por_bioma(bioma_sel)
                region_id = st.selectbox("📍 Región", regiones)
                versiones_raw = listar_versiones_disponibles(region_id)
            else:
                region_id = "BIOMA"
                versiones_raw = listar_assets_por_bioma(bioma_sel)

            if not versiones_raw:
                st.warning("No hay assets disponibles para la selección.")
                st.stop()

            if scope == "bioma":
                version_sel = seleccionar_assets_base_ultima_version_efectiva(versiones_raw)
                if not version_sel:
                    st.warning(
                        "No se encontraron mapas base de estadísticas (R{id}_V{versión} sin proceso) para este bioma."
                    )
                    st.stop()
                st.subheader("Mapas incluidos (bioma)")
                st.caption(
                    "Última versión efectiva **por región** (sin sufijos). "
                    "La etiqueta **V11** no se usa como última cuando existen otras versiones base."
                )
                st.success(f"Incluye **{len(version_sel)}** regiones ({len(version_sel)} assets base).")
                with st.expander("Lista de assets (último base por región)"):
                    for aid in sorted(version_sel, key=lambda x: x.split("/")[-1]):
                        st.text(aid.split("/")[-1])
            else:
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
        st.divider()


        

    return region_id, version_sel, modo_vista, modo, scope, bioma_sel
