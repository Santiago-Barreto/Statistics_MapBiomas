"""
Módulo de Estado - MapBiomas Colombia
Visualiza el historial de sincronización y novedades del sistema.
"""

import streamlit as st
import datetime
from sync.manager import obtener_resumen_sincro
from ui.formatters import organizar_reporte_novedades

def render_status_popover():
    """
    Renderiza el estado de la última sincronización y el reporte de novedades.
    """
    ts, total, nombres_raw = obtener_resumen_sincro()
    
    st.markdown("### 🔄 Estado de Sincronización")
    
    if ts:
        hora_local = datetime.datetime.fromtimestamp(ts)
        st.caption(f"Última vez: {hora_local.strftime('%H:%M:%S')}")
        
        if total > 0:
            st.info(f"✨ {total} Assets nuevos detectados")
            with st.expander("Ver detalle de novedades"):
                novedades = organizar_reporte_novedades(nombres_raw)
                for reg, items in novedades.items():
                    st.markdown(f"**Región {reg}:**")
                    for i in items:
                        st.write(f"- {i.split('/')[-1]}")
    else:
        st.caption("Sincronización pendiente o sin registros.")