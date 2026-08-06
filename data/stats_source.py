"""
Fuente activa de estadísticas (Colección MapBiomas vs STATISTICS_GENERAL).

Por defecto se usa la colección estable. STATISTICS_GENERAL es una carpeta
aparte para análisis sin alterar MapBiomas.
"""

from __future__ import annotations

from config import (
    ASSET_PARENT,
    ASSET_PARENT_GENERAL,
    FUENTE_DEFAULT,
    FUENTE_GENERAL,
    FUENTES_ESTADISTICAS,
)


def parent_para_fuente(fuente: str) -> str:
    """Resuelve la carpeta GEE según la clave de fuente."""
    if fuente == FUENTE_GENERAL:
        return ASSET_PARENT_GENERAL.rstrip("/") + "/"
    return ASSET_PARENT.rstrip("/") + "/"


def label_para_fuente(fuente: str) -> str:
    for label, key in FUENTES_ESTADISTICAS.items():
        if key == fuente:
            return label
    return fuente


def get_fuente_activa() -> str:
    """Clave de fuente en session_state (o default si no hay Streamlit)."""
    try:
        import streamlit as st

        return st.session_state.get("fuente_stats", FUENTE_DEFAULT)
    except Exception:
        return FUENTE_DEFAULT


def get_active_asset_parent() -> str:
    """Carpeta GEE de estadísticas para la sesión actual."""
    return parent_para_fuente(get_fuente_activa())


def set_fuente_activa(fuente: str) -> bool:
    """
    Actualiza la fuente en session_state.

    Returns:
        True si la fuente cambió respecto al valor anterior.
    """
    import streamlit as st

    if fuente not in FUENTES_ESTADISTICAS.values():
        fuente = FUENTE_DEFAULT
    anterior = st.session_state.get("fuente_stats", FUENTE_DEFAULT)
    st.session_state.fuente_stats = fuente
    return anterior != fuente
