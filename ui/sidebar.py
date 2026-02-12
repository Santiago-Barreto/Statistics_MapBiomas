"""
Módulo de Interfaz Lateral - MapBiomas Colombia
Renderiza la configuración, el registro de sincronización y herramientas de validación externa.
"""

import streamlit as st
import datetime
from gee.assets import obtener_biomas, regiones_por_bioma, listar_versiones_disponibles
from sync.manager import obtener_resumen_sincro
from ui.formatters import formatear_nombre_humano, categorizar_versiones, organizar_reporte_novedades

def render_sidebar():
    """
    Renderiza los controles de navegación y herramientas adicionales en la barra lateral.
    """
    with st.sidebar:
        st.header("Configuración")

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
        
        ts, total, nombres_raw = obtener_resumen_sincro()
        if ts:
            hora_local = datetime.datetime.fromtimestamp(ts) - datetime.timedelta(hours=5)
            fecha_dt = hora_local.strftime('%H:%M:%S')
            st.caption(f"🔄 Sincronización: {fecha_dt}")
            
            if total > 0:
                with st.expander(f"✨ {total} Assets nuevos"):
                    novedades_por_region = organizar_reporte_novedades(nombres_raw)
                    for reg, items in novedades_por_region.items():
                        st.markdown(f"**Región {reg}:**")
                        for i in items:
                            st.write(f"- {i}")
        else:
            st.caption("🔄 Sincronización pendiente...")

        st.divider()

        st.subheader("Validación Externa")
        st.info("Compara los resultados de la Colección 4 frente a la Colección 3 en el visor oficial (También puedes ver los limites entre regiones y biomas ;D)")
        
        st.link_button(
            "🔍 Visor Comparativo C3 vs C4",
            "https://mapbiomas-andesnorte.users.earthengine.app/view/coleccion4",
            use_container_width=True,
            help="Accede a la App de GEE para validación cruzada entre colecciones."
        )

    return region_id, version_sel, modo_vista