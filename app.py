import streamlit as st
from gee.init import inicializar_gee
from gee.assets import listar_versiones_disponibles, leer_stats_procesadas
from data.processing import construir_dataframe, fusionar_versiones
from ui.charts import plot_temporal_series, render_metrics

st.set_page_config(page_title="MapBiomas Dashboard", layout="wide", page_icon="🌱")
inicializar_gee()

st.title("🌱 Estadísticas MapBiomas")

with st.sidebar:
    st.header("Configuración")
    region_id = st.text_input("ID de Región", value="R30205")
    
    versiones_disponibles = listar_versiones_disponibles(region_id)
    
    if not versiones_disponibles:
        st.warning("No se hallaron versiones.")
        st.stop()
        
    version_sel = st.multiselect("Seleccionar Versiones", 
                               options=versiones_disponibles, 
                               default=versiones_disponibles[:1])

@st.cache_data(show_spinner="Cargando datos...")
def cargar_todo(region, lista_versiones):
    results = []
    for v in lista_versiones:
        raw = leer_stats_procesadas(f"{region}_{v}")
        df_v = construir_dataframe(raw, v)
        if df_v is not None:
            results.append(df_v)
    return fusionar_versiones(results)

if version_sel:
    df = cargar_todo(region_id, version_sel)
    
    if df is not None and not df.empty:
        render_metrics(df)
        plot_temporal_series(df, region_id)
        
        with st.expander("📊 Tabla de datos"):
            st.dataframe(df.sort_values(["version", "year"]), width='stretch')
    else:
        st.error("No hay datos para las versiones seleccionadas.")
else:
    st.info("Selecciona al menos una versión en el panel izquierdo.")
