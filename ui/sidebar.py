"""
Módulo de Interfaz Lateral - MapBiomas Colombia
Renderiza la configuración, el registro de sincronización y herramientas de validación externa.
"""

import streamlit as st
from gee.assets import (
    obtener_biomas,
    regiones_por_bioma,
    listar_versiones_disponibles,
)
from ui.formatters import (
    formatear_nombre_humano,
    categorizar_versiones,
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
        st.caption("Rama local de pruebas · SQLite")
        if st.button("🔄 Sincronizar ahora", use_container_width=True):
            st.session_state.forzar_sincro = True
            st.rerun()
        if st.button(
            "♻️ Reexportar estadísticas GEE",
            use_container_width=True,
            help=(
                "Vuelve a descargar TODAS las stats desde "
                "mapbiomas-colombia/.../ESTADISTICAS y sobrescribe la BD local. "
                "Elimina copias de otros proyectos. Puede tardar varios minutos."
            ),
        ):
            st.session_state.forzar_reexport_stats = True
            st.rerun()
        st.divider()

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
                versiones_raw = []

            if scope == "region" and not versiones_raw:
                st.warning("No hay assets disponibles para la selección.")
                st.stop()

            if scope == "bioma":
                from data.asset_final import resolver_assets_bioma_desde_avance

                resolucion = resolver_assets_bioma_desde_avance(bioma_sel)
                version_sel = resolucion.asset_ids

                st.subheader("Mapas incluidos (bioma)")
                st.caption(
                    "Versiones según **Asset Final** "
                    "(hoja MAPA GENERAL COLOMBIA · columna CJ del avance Col. 4)."
                )

                if resolucion.faltantes and not version_sel and "No se encontró" in (
                    resolucion.faltantes[0] if resolucion.faltantes else ""
                ):
                    st.error(resolucion.faltantes[0])
                    st.stop()

                if not version_sel:
                    st.warning(
                        f"Ningún Asset Final del bioma **{bioma_sel}** está en la BD. "
                        "Sincroniza estadísticas o revisa el Excel de avance."
                    )
                    st.stop()

                st.success(
                    f"Incluye **{len(version_sel)}** regiones "
                    f"(Asset Final cruzado con la BD)."
                )
                if resolucion.faltantes:
                    with st.expander(
                        f"⚠️ {len(resolucion.faltantes)} Asset Final sin estadísticas en BD"
                    ):
                        st.caption("Se omiten del análisis; no detienen la vista.")
                        for lab in resolucion.faltantes:
                            st.text(lab)
                if resolucion.invalidos:
                    with st.expander(
                        f"ℹ️ {len(resolucion.invalidos)} valores inválidos en columna CJ"
                    ):
                        for lab in resolucion.invalidos:
                            st.text(lab)

                with st.expander("Lista de assets (Asset Final → estadísticas)"):
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
            modo_vista = st.radio(
                "Visualización",
                ["Dashboard Completo", "Solo Gráficas", "Comparativa Combinada"],
            )

            if scope == "region":
                _render_exportar_version_final(region_id, version_sel)

            st.divider()

            st.subheader("Comparación en GEE")
            st.info(
                "Compara los resultados de la Colección 4 frente a la Colección 3 en el visor oficial "
                "(También puedes ver los limites entre regiones y biomas ;D)"
            )

            st.link_button(
                "🔍 Visor Comparativo C3 vs C4",
                "https://mapbiomas-andesnorte.users.earthengine.app/view/coleccion4",
                width="content",
                help="Accede a la App de GEE para validación cruzada entre colecciones.",
            )
        st.divider()

    return region_id, version_sel, modo_vista, modo, scope, bioma_sel


def _excel_script_fingerprint() -> str:
    """Cambia si se edita export/excel_charts.py → invalida Excel en session_state."""
    import hashlib
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "export" / "excel_charts.py"
    try:
        raw = path.read_bytes()
        return hashlib.md5(raw).hexdigest()[:10]
    except OSError:
        return "0"


def _render_exportar_version_final(region_id, version_sel):
    """Botón bajo Visualización: Excel con gráficas desde las versiones seleccionadas."""
    import importlib

    from export import excel_charts as _excel_mod

    # Recarga el módulo si el .py cambió (Streamlit a veces conserva el import viejo).
    _excel_mod = importlib.reload(_excel_mod)
    script_fp = _excel_script_fingerprint()

    st.caption(
        "Una hoja por versión + gráficas MapBiomas → descarga "
        f"`region_{region_id}_complete.xlsx`."
    )
    disabled = not version_sel
    if st.button(
        "📥 Exportar versión final",
        use_container_width=True,
        disabled=disabled,
        help="Requiere marcar al menos una versión arriba.",
        key=f"btn_export_final_{script_fp}",
    ):
        from data.processing import cargar_datos_totales

        with st.spinner("Generando Excel…"):
            data_dict = cargar_datos_totales(version_sel)
            if not data_dict:
                st.error("No hay estadísticas en la BD para esas versiones. Sincroniza primero.")
            else:
                payload = _excel_mod.generar_excel_con_graficas_desde_data_dict(data_dict)
                st.session_state["excel_final"] = {
                    "bytes": payload,
                    "name": f"region_{region_id}_complete.xlsx",
                    "n": len(data_dict),
                    "sig": tuple(sorted(version_sel)),
                    "script_fp": script_fp,
                }

    excel = st.session_state.get("excel_final")
    # Invalidar si cambió la selección o el script de exportación.
    if excel and (
        excel.get("sig") != tuple(sorted(version_sel or []))
        or excel.get("script_fp") != script_fp
    ):
        st.session_state.pop("excel_final", None)
        excel = None
    if excel:
        st.download_button(
            label=f"⬇️ Descargar {excel['name']} ({excel['n']} hojas)",
            data=excel["bytes"],
            file_name=excel["name"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_excel_final_{script_fp}",
        )
