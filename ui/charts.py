import plotly.express as px
import streamlit as st

def plot_temporal_series(df, region_id):
    cols_stats = [c for c in df.columns if c not in ["year", "version"]]
    
    if len(df["version"].unique()) == 1:
        df_long = df.melt(id_vars=["year"], value_vars=cols_stats, var_name="Cobertura", value_name="Hectáreas")
        fig = px.line(df_long, x="year", y="Hectáreas", color="Cobertura", markers=True, 
                     title=f"Región {region_id} - {df['version'].iloc[0]}", template="plotly_white")
    else:
        cobertura = st.selectbox("Selecciona Cobertura para comparar versiones:", cols_stats)
        fig = px.line(df, x="year", y=cobertura, color="version", markers=True,
                     title=f"Comparativa de {cobertura} entre versiones", template="plotly_white")
    
    st.plotly_chart(fig, width='stretch')

def render_metrics(df):
    c1, c2, c3 = st.columns(3)
    c1.metric("Años", f"{df['year'].min()} - {df['year'].max()}")
    c2.metric("Versiones", df['version'].nunique())
    c3.metric("Coberturas", len([c for c in df.columns if c not in ["year", "version"]]))