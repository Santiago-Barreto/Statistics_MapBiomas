"""
Módulo de Administración - MapBiomas Colombia
Gestión de borrado físico en GEE y lógico en SQLite.
"""

import streamlit as st
import ee
import time
from data.db import get_conn, ph
from config import ASSET_PARENT
from gee.assets import listar_versiones_disponibles, listar_assets_por_bioma
from gee.deletion import (
    es_asset_clasificacion,
    es_asset_eliminable,
    es_error_asset_inexistente,
    es_ruta_protegida,
    expandir_assets_para_eliminar,
)

def obtener_assets_totales():
    """
    Obtiene la lista completa de IDs de assets desde las carpetas de GEE.
    """
    try:
        assets = ee.data.listAssets({'parent': ASSET_PARENT}).get('assets', [])
        return [a['id'] for a in assets]
    except Exception as e:
        st.error(f"Error al consultar GEE: {str(e)}")
        return []

def eliminar_assets_seleccionados(lista_ids):
    """
    Elimina assets de estadísticas en GEE y SQLite, y el asset de clasificación
    pareado (clasificacion / clasificacion-ft). Rutas padre están bloqueadas.
    """
    resultados = {"exitos": [], "errores": [], "bloqueados": [], "omitidos": []}
    candidatos = expandir_assets_para_eliminar(lista_ids)
    stats_prefix = ASSET_PARENT.rstrip("/") + "/"

    para_eliminar = []
    for a_id in candidatos:
        if es_ruta_protegida(a_id):
            resultados["bloqueados"].append(
                f"BLOQUEADO: {a_id.split('/')[-1]} es una carpeta protegida"
            )
            continue
        ok, motivo = es_asset_eliminable(a_id)
        if not ok:
            resultados["bloqueados"].append(f"BLOQUEADO: {motivo}")
            continue
        para_eliminar.append(a_id)

    if not para_eliminar:
        return resultados

    conn = get_conn()
    cur = conn.cursor()

    for a_id in para_eliminar:
        try:
            ee.data.deleteAsset(a_id)
            if a_id.startswith(stats_prefix):
                cur.execute(f"DELETE FROM assets WHERE asset_id = {ph()}", (a_id,))
                cur.execute(f"DELETE FROM stats WHERE asset_id = {ph()}", (a_id,))
            resultados["exitos"].append(a_id)
        except Exception as e:
            if es_asset_clasificacion(a_id) and es_error_asset_inexistente(e):
                resultados["omitidos"].append(
                    f"Clasificación no encontrada (omitida): {a_id.split('/')[-1]}"
                )
                continue
            resultados["errores"].append(f"Error en {a_id.split('/')[-1]}: {str(e)}")

    conn.commit()
    conn.close()
    return resultados

def render_admin_zone(modo, region_id=None, bioma_sel=None):
    """
    Interfaz administrativa para eliminación de assets según la región activa.
    """
    with st.expander("🗑️ Gestión Administrativa de Assets"):
        st.warning("⚠️ Los cambios realizados aquí afectan directamente a Google Earth Engine.")

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
        
        st.caption(
            "Al eliminar una versión de estadísticas también se intenta borrar su asset de "
            "clasificación en GEE. Si la clasificación no existe, se omite y se borra solo la estadística."
        )

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
                    res = eliminar_assets_seleccionados(assets_a_eliminar)
                    if res["exitos"]:
                        st.success(
                            f"Eliminados {len(res['exitos'])} assets en GEE "
                            f"({len(assets_a_eliminar)} versión/es seleccionada/s)."
                        )
                        time.sleep(1)
                        st.rerun()
                    if res["omitidos"]:
                        for msg in res["omitidos"]:
                            st.info(msg)
                    if res["bloqueados"]:
                        for msg in res["bloqueados"]:
                            st.warning(msg)
                    if res["errores"]:
                        for err in res["errores"]:
                            st.error(err)
        else:
            st.info("💡 No es necesario activar versiones para eliminarlas.")