import plotly.express as px
import streamlit as st
from config import LEYENDA_MAPBIOMAS

def obtener_configuracion_visual(columnas):
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

def render_metrics_agricultura(df):
    """Muestra métricas resumidas para agricultura."""
    c1, c2 = st.columns(2)
    c1.metric("Años", f"{df['year'].min()} - {df['year'].max()}")
    metrics = [c for c in df['metric'].unique()]
    c2.metric("Métricas", len(metrics))

def plot_temporal_series_agricultura(df, region_id):
    """
    Genera gráficos de serie temporal para agricultura.
    """
    df = df.sort_values("year").reset_index(drop=True)
    metrics = df['metric'].unique()
    color_map, label_map = obtener_configuracion_visual(metrics)

    df_long = df.copy()
    df_long['Cobertura'] = df_long['metric'].map(label_map)
    df_long = df_long.rename(columns={'value': 'Hectáreas'})

    fig = px.line(
        df_long, x='year', y='Hectáreas', color='Cobertura', markers=True,
        title=f"Serie Temporal Agricultura - Región {region_id}",
        template="plotly_white",
        color_discrete_map=color_map
    )
    st.plotly_chart(fig, width='stretch')
