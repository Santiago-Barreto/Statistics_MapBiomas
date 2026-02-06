"""
Módulo de Inspección Geoespacial - MapBiomas Colombia
Proporciona herramientas para la recuperación de geometrías y la generación 
de visualizaciones rápidas (thumbnails) desde Google Earth Engine.
"""

import ee
import streamlit as st
import re
from config import BASE_PATH_V1, BASE_PATH_VX, ASSET_REGIONES, MAPBIOMAS_PALETTE
from data.processing import extraer_label_version

@st.cache_data(show_spinner=False)
def obtener_region_geom(region_id):
    """
    Recupera la geometría vectorial de una región específica.

    Args:
        region_id (str): Identificador de la región (ej. 'R30205').
    
    Returns:
        ee.Geometry: Geometría para operaciones de recorte (clip).
    """
    clean_id = int(re.sub(r"\D", "", str(region_id)))
    return ee.FeatureCollection(ASSET_REGIONES).filter(
        ee.Filter.eq("id_regionC", clean_id)
    ).geometry()

@st.cache_data(show_spinner=False)
def get_thumbnail_url(_geom, year, asset_version):
    """
    Genera una URL de miniatura para una clasificación anual específica.

    Args:
        _geom (ee.Geometry): Geometría de recorte.
        year (int): Año de la clasificación.
        asset_version (str): Nombre del asset para extraer región y versión.

    Returns:
        str: URL de la imagen PNG generada por GEE o None en caso de error.
    """
    try:
        region_match = re.search(r'R(\d+)', asset_version)
        version_match = re.search(r'[V-](\d+)', asset_version)

        if not region_match:
            return None

        region_id = region_match.group(1)
        version_num = version_match.group(1) if version_match else "1"
        base_path = BASE_PATH_V1 if version_num == "1" else BASE_PATH_VX
        
        full_asset_path = f"{base_path}/COLOMBIA-{region_id}-{version_num}"

        img = ee.Image(full_asset_path).select(f"classification_{year}").clip(_geom)
        
        return img.getThumbURL({
            "min": 0,
            "max": 99,
            "palette": MAPBIOMAS_PALETTE,
            "dimensions": 512,
            "format": "png"
        })
    except Exception as e:
        st.sidebar.error(f"Error en GEE: {e}") # Esto te dirá el error real en la app
        return None
    
def render_visual_inspector(region_id, version_sel, data_dict):
    """
    Renderiza la interfaz de inspección visual utilizando un selector numérico
    sincronizado con el estado global de la sesión.
    """
    st.subheader("🔍 Inspección Visual Histórica")
    
    primer_df = next(iter(data_dict.values()))
    min_y = int(primer_df['year'].min())
    max_y = int(primer_df['year'].max())

    default_year = st.session_state.get("selected_year", max_y)
    
    c_year, c_ver, c_btn = st.columns([1, 1, 1])
    
    with c_year:
        año_ver = st.number_input(
            label="Año central:", 
            min_value=min_y, 
            max_value=max_y, 
            value=default_year,
            step=1,
            format="%d"
        )
        st.session_state.selected_year = año_ver

    with c_ver:
        v_mapa = st.selectbox(
                    "Versión en mapa:", 
                    version_sel,
                    format_func=extraer_label_version
                )
    with c_btn:
        st.write(" ") 
        if st.button("🔍 Comparar T-1 · T · T+1", use_container_width=True):

            with st.spinner(f"Generando vistas para {año_ver}..."):
                geom = obtener_region_geom(region_id)
                anios = [año_ver - 1, año_ver, año_ver + 1]
                st.session_state.thumbnails = {
                    "año": año_ver,
                    "items": [(y, get_thumbnail_url(geom, y, v_mapa)) for y in anios]
                }

    if st.session_state.thumbnails:
        cols = st.columns(3)
        for col, (anio, url) in zip(cols, st.session_state.thumbnails["items"]):
            with col:
                if url:
                    st.image(url, caption=f"Año {anio}", width='stretch')
                else:
                    st.caption(f"⚠️ Sin datos para {anio}")
        
        if st.button("🗑️ Limpiar vistas"):
            st.session_state.thumbnails = None
            st.rerun()