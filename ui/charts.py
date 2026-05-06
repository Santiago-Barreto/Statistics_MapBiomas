import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from data.processing import fusionar_versiones
from data.biome_analysis import construir_heatmap_cambios, construir_tabla_linea_temporal
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
    df = df.sort_values("year").reset_index(drop=True)
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
        df_unificado = df_unificado.sort_values(["version", "year"])
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

def render_biome_view(data_dict, biome):
    """Renderiza solo los gráficos en cuadrícula de 2 columnas."""
    cols_g = st.columns(2)
    for i, (v, df) in enumerate(data_dict.items()):
        with cols_g[i % 2]:
            st.markdown(f"#### 📈 Versión {v}")
            plot_temporal_series(df, biome)
            st.divider()


def _label_clase(class_id):
    """Convierte IDs técnicos (ID03) en etiquetas legibles de cobertura."""
    try:
        class_num = int(str(class_id).replace("ID", ""))
    except ValueError:
        return str(class_id)
    return LEYENDA_MAPBIOMAS.get(class_num, {}).get("label", str(class_id))


def render_regional_contributions_biome(df_regional, biome):
    """
    Muestra análisis por región para una cobertura del bioma:
    - heatmap anotado de ganancias/pérdidas interanuales
    - tabla de línea temporal con cambios anuales
    """
    if df_regional is None or df_regional.empty:
        return

    st.markdown(f"### 🧭 Aportes regionales · Bioma {biome}")
    st.caption(
        "Identifica qué regiones explican el total del bioma y cuáles impulsan las ganancias o pérdidas por cobertura."
    )

    clases = sorted(df_regional["class_id"].dropna().unique().tolist())
    anios = sorted(df_regional["year"].dropna().unique().tolist())
    if not clases or not anios:
        return

    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        clase_sel = st.selectbox(
            "Cobertura",
            options=clases,
            format_func=_label_clase,
            key=f"bioma_aporte_clase_{biome}",
        )
    with c2:
        st.metric("Años analizados", f"{anios[0]} - {anios[-1]}")
    with c3:
        st.metric("Cobertura", _label_clase(clase_sel))

    df_cov = df_regional[df_regional["class_id"] == clase_sel].copy()
    if df_cov.empty:
        st.info("No hay datos para la cobertura seleccionada.")
        return

    df_heat = construir_heatmap_cambios(df_cov)
    if df_heat.empty or df_heat.shape[1] == 0:
        st.info("Se requieren al menos dos años para calcular ganancias y pérdidas.")
        return

    st.markdown("#### Heatmap de ganancias y pérdidas por región")
    zmax = float(df_heat.abs().to_numpy().max()) if not df_heat.empty else 0.0
    if zmax == 0:
        zmax = 1.0

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=df_heat.values,
            x=df_heat.columns.tolist(),
            y=df_heat.index.tolist(),
            colorscale="RdYlGn",
            zmid=0,
            zmin=-zmax,
            zmax=zmax,
            colorbar={"title": "Δ ha"},
            text=[[f"{v:,.0f}" for v in row] for row in df_heat.values],
            texttemplate="%{text}",
            textfont={"size": 11},
        )
    )
    fig_heat.update_layout(
        template="plotly_white",
        xaxis_title="Periodo",
        yaxis_title="Región",
        margin={"l": 20, "r": 20, "t": 10, "b": 10},
    )
    st.plotly_chart(fig_heat, width="stretch")

    st.markdown("#### Línea temporal completa (ha, ganancia/pérdida anual)")
    tabla_tiempo = construir_tabla_linea_temporal(df_cov)
    st.dataframe(tabla_tiempo, width="stretch")
