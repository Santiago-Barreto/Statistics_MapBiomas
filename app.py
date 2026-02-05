import streamlit as st
from gee.init import inicializar_gee
from gee.assets import listar_versiones_disponibles, leer_stats_procesadas
from data.processing import construir_dataframe
from ui.charts import plot_temporal_series, render_metrics

st.set_page_config(page_title="MapBiomas Dashboard", layout="wide", page_icon="🌱")
inicializar_gee()

st.title("🌱 Estadísticas MapBiomas")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Configuración")
    region_id = st.text_input("ID de Región", value="R30205")

    versiones_disponibles = sorted(listar_versiones_disponibles(region_id))

    if not versiones_disponibles:
        st.warning("No se hallaron versiones.")
        st.stop()

    version_sel = st.multiselect(
        "Seleccionar Versiones",
        options=versiones_disponibles,
        default=versiones_disponibles[:1]
    )

    modo_vista = st.radio(
        "Modo de visualización",
        ["Completo", "Solo gráficas"],
        horizontal=True
    )

# ---------------- Data loader ----------------
@st.cache_data(show_spinner=False)
def cargar_por_version(region, lista_versiones):
    data = {}
    for v in lista_versiones:
        raw = leer_stats_procesadas(f"{region}_{v}")
        df = construir_dataframe(raw, v)
        if df is not None and not df.empty:
            data[v] = df
    return data

# ---------------- Main ----------------
if not version_sel:
    st.info("Selecciona al menos una versión en el panel izquierdo.")
    st.stop()

data_por_version = cargar_por_version(region_id, version_sel)

if not data_por_version:
    st.error("No hay datos para las versiones seleccionadas.")
    st.stop()

# ================= MODO COMPLETO =================
if modo_vista == "Completo":
    tabs = st.tabs([f"Versión {v}" for v in data_por_version])

    for tab, (v, df) in zip(tabs, data_por_version.items()):
        with tab:
            with st.spinner(f"Cargando versión {v}..."):
                st.caption(f"📅 Años disponibles: {df['year'].nunique()}")

                with st.expander("📊 Métricas", expanded=False):
                    render_metrics(df)

                plot_temporal_series(df, region_id)

                with st.expander("🧾 Tabla de datos"):
                    st.dataframe(
                        df.sort_values("year"),
                        width="stretch"
                    )

# ================= SOLO GRÁFICAS =================
elif modo_vista == "Solo gráficas":
    st.subheader("📈 Comparación visual por versión")

    for v, df in data_por_version.items():
        with st.spinner(f"Cargando gráfica {v}..."):
            st.markdown(f"### 🌱 Versión {v}")
            plot_temporal_series(df, region_id)
