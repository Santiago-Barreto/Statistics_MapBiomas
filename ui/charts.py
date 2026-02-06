import plotly.express as px
import streamlit as st
from data.processing import fusionar_versiones
from config import LEYENDA_MAPBIOMAS

def obtener_configuracion_visual(columnas):
    """
    Genera mapeos de colores y nombres legibles a partir de la leyenda.

    Args:
        columnas (list): Lista de columnas tipo ID (ej. ['ID03', 'ID21']).

    Returns:
        tuple: (diccionario_colores, diccionario_nombres).
    """
    color_map = {}
    label_map = {}
    
    for col in columnas:
        try:
            id_num = int(col.replace("ID", ""))
            info = LEYENDA_MAPBIOMAS.get(id_num, {"label": col, "color": "#cccccc"})
            color_map[col] = info["color"]
            label_map[col] = info["label"]
        except ValueError:
            label_map[col] = col
            
    return color_map, label_map

def render_metrics(df):
    """Muestra métricas resumidas: años, versiones y número de coberturas."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Años", f"{df['year'].min()} - {df['year'].max()}")
    c2.metric("Versiones", df['version'].nunique())
    coberturas = [c for c in df.columns if c not in ["year", "version"]]
    c3.metric("Coberturas", len(coberturas))

def plot_temporal_series(df, region_id):
    """
    Genera gráficos interactivos con etiquetas reales en la leyenda.
    """
    cols_stats = [c for c in df.columns if c not in ["year", "version"]]
    color_map, label_map = obtener_configuracion_visual(cols_stats)
    
    if df["version"].nunique() == 1:
        df_long = df.melt(
            id_vars=["year"], value_vars=cols_stats, 
            var_name="Cobertura", value_name="Hectáreas"
        )
        
        df_long["Cobertura"] = df_long["Cobertura"].map(label_map)
        
        fig = px.line(
            df_long, x="year", y="Hectáreas", color="Cobertura", markers=True, 
            title=f"Tendencia: {region_id}", 
            template="plotly_white",
            color_discrete_map={label_map[k]: v for k, v in color_map.items()}
        )
    else:
        key_sel = f"sel_comb_{region_id}"
        opcion_id = st.selectbox(
            "Seleccionar Cobertura:", 
            options=cols_stats, 
            format_func=lambda x: label_map.get(x, x),
            key=key_sel
        )
        
        fig = px.line(
            df, x="year", y=opcion_id, color="version", markers=True,
            title=f"Evolución: {label_map.get(opcion_id)}", 
            template="plotly_white"
        )
    
    st.plotly_chart(fig, width='stretch')

def render_combined_view(data_dict, region_id):
    """
    Renderiza una vista unificada donde se compara una sola cobertura 
    a través de todas las versiones activas.
    """
    st.markdown(f"#### 🧬 Comparativa Multiversión: Región {region_id}")
    
    df_unificado = fusionar_versiones(list(data_dict.values()))
    
    if df_unificado is not None:
        render_metrics(df_unificado)
        plot_temporal_series(df_unificado, region_id)
        
        with st.expander("📋 Datos Consolidados"):
            st.dataframe(df_unificado, width='stretch')
            
def render_dashboard_view(data_dict, region_id):
    """Renderiza pestañas con métricas, gráficos y tabla de datos."""
    tabs = st.tabs([f"Versión {v}" for v in data_dict.keys()])
    for tab, (v, df) in zip(tabs, data_dict.items()):
        with tab:
            render_metrics(df)
            plot_temporal_series(df, region_id)
            with st.expander("📋 Tabla de Datos"):
                st.dataframe(df.sort_values("year", ascending=False),
                             width='stretch')

def render_graphs_only_view(data_dict, region_id):
    """Renderiza solo los gráficos en cuadrícula de 2 columnas."""
    cols_g = st.columns(2)
    for i, (v, df) in enumerate(data_dict.items()):
        with cols_g[i % 2]:
            st.markdown(f"#### 📈 Versión {v}")
            plot_temporal_series(df, region_id)
            st.divider()
