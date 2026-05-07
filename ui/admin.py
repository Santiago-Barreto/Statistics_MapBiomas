"""
Módulo de Administración - MapBiomas Colombia
Gestión de borrado físico en GEE y lógico en SQLite.
"""

import streamlit as st
import ee
import time
from data.db import get_conn
from config import ASSET_PARENT, ASSET_PARENT_AGRICULTURA
from gee.assets import listar_versiones_disponibles, listar_assets_por_bioma

def obtener_assets_totales(es_agricultura=False):
    """
    Obtiene la lista completa de IDs de assets desde las carpetas de GEE.
    """
    try:
        carpeta = ASSET_PARENT_AGRICULTURA if es_agricultura else ASSET_PARENT
        assets = ee.data.listAssets({'parent': carpeta}).get('assets', [])
        return [a['id'] for a in assets]
    except Exception as e:
        st.error(f"Error al consultar GEE: {str(e)}")
        return []

def eliminar_assets_seleccionados(lista_ids, es_agricultura=False):
    """
    Elimina assets de Google Earth Engine y sus registros en la base de datos local.
    """
    conn = get_conn()
    cur = conn.cursor()
    resultados = {"exitos": [], "errores": []}

    for a_id in lista_ids:
        try:
            ee.data.deleteAsset(a_id)
            if es_agricultura:
                cur.execute("DELETE FROM stats_agricultura WHERE asset_id = ?", (a_id,))
            else:
                cur.execute("DELETE FROM assets WHERE asset_id = ?", (a_id,))
                cur.execute("DELETE FROM stats WHERE asset_id = ?", (a_id,))
            resultados["exitos"].append(a_id)
        except Exception as e:
            resultados["errores"].append(f"Error en {a_id.split('/')[-1]}: {str(e)}")
    
    conn.commit()
    conn.close()
    return resultados

def render_admin_zone(modo, region_id=None, bioma_sel=None):
    """
    Interfaz administrativa para eliminación de assets según la región activa.
    """
    es_agricultura = (modo == 'agricultura')
    
    with st.expander("🗑️ Gestión Administrativa de Assets"):
        st.warning("⚠️ Los cambios realizados aquí afectan directamente a Google Earth Engine.")
        
        if es_agricultura:
            version_pool = obtener_assets_totales(es_agricultura=True)
        else:
            if str(region_id) == "BIOMA" and bioma_sel:
                version_pool = listar_assets_por_bioma(bioma_sel)
            elif not region_id:
                st.info("💡 Selecciona una región en el panel lateral.")
                return
            elif str(region_id) == "BIOMA":
                st.info("💡 Vista bioma: elige un bioma en el panel lateral y vuelve a abrir este diálogo.")
                return
            else:
                version_pool = listar_versiones_disponibles(region_id)
        
        if not version_pool:
            st.info("💡 No se encontraron assets físicos en GEE para esta configuración.")
            return
        
        unique_key = f"admin_{modo}_{hash(tuple(version_pool))}"
        
        assets_a_eliminar = st.multiselect(
            "Selecciona los assets para eliminar:",
            options=version_pool,
            key=f"multi_{unique_key}",
            format_func=lambda x: x.split('/')[-1]
        )
        
        if assets_a_eliminar:
            col1, col2 = st.columns([3, 1])
            with col1:
                confirmar = st.checkbox("Confirmar eliminación permanente", key=f"check_{unique_key}")
            with col2:
                if st.button("🔥 EJECUTAR", disabled=not confirmar, use_container_width=True, key=f"btn_{unique_key}"):
                    res = eliminar_assets_seleccionados(assets_a_eliminar, es_agricultura)
                    if res["exitos"]:
                        st.success(f"Eliminados {len(res['exitos'])} assets.")
                        time.sleep(1)
                        st.rerun()
                    if res["errores"]:
                        for err in res["errores"]:
                            st.error(err)
        else:
            st.info("💡 No es necesario activar versiones para eliminarlas.")