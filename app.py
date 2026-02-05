import streamlit as st
import pandas as pd
import plotly.express as px
import gee_utils
gee_utils.inicializar_gee()
# --------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------
st.set_page_config(
    page_title="Dashboard MapBiomas - Café",
    layout="wide"
)

st.title("☕ Estadísticas Procesadas - Proyecto Café")

# --------------------------------------------
# SIDEBAR
# --------------------------------------------
st.sidebar.header("Configuración")

region_id = st.sidebar.text_input(
    "Región:",
    value="R30205"
)

versiones_disponibles = ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]

versiones = st.sidebar.multiselect(
    "Versiones:",
    options=versiones_disponibles,
    default=["V1"]
)

modo = st.sidebar.radio(
    "Modo de visualización:",
    ["Individual", "Comparación", "Combinada"]
)

st.sidebar.markdown("---")
st.sidebar.caption("MapBiomas Colombia – Colección 4")

# --------------------------------------------
# FUNCIONES
# --------------------------------------------
@st.cache_data(show_spinner=False)
def cargar_version(region_id, version):
    asset_name = f"{region_id}_{version}"
    try:
        data = gee_utils.leer_stats_procesadas(asset_name)
    except Exception:
        return None

    if not data:
        return None

    df = pd.DataFrame(data)

    columnas_ignorar = ['system:index', 'geo']
    df = df.drop(columns=[c for c in columnas_ignorar if c in df.columns])

    df['year'] = df['year'].astype(int)
    df['version'] = version

    return df


def cargar_datos(region_id, versiones):
    dfs = []
    for v in versiones:
        df_v = cargar_version(region_id, v)
        if df_v is not None:
            dfs.append(df_v)
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)


# --------------------------------------------
# EJECUCIÓN
# --------------------------------------------
if st.button("Visualizar estadísticas"):
    with st.spinner("Cargando datos desde GEE Assets..."):
        df_all = cargar_datos(region_id, versiones)

    if df_all is None:
        st.error("No se pudieron cargar los Assets seleccionados.")
        st.stop()

    columnas_cobertura = [
        c for c in df_all.columns if c not in ['year', 'version']
    ]

    # ----------------------------------------
    # MODO INDIVIDUAL
    # ----------------------------------------
    if modo == "Individual":
        version_sel = st.selectbox(
            "Selecciona versión:",
            versiones
        )

        df_v = df_all[df_all['version'] == version_sel]

        df_long = df_v.melt(
            id_vars=['year'],
            var_name='Cobertura',
            value_name='Hectáreas'
        )

        fig = px.line(
            df_long,
            x='year',
            y='Hectáreas',
            color='Cobertura',
            markers=True,
            title=f"{region_id} – {version_sel}",
            template="plotly_white"
        )

        st.plotly_chart(fig, use_container_width=True)

    # ----------------------------------------
    # MODO COMPARACIÓN
    # ----------------------------------------
    elif modo == "Comparación":
        cobertura = st.selectbox(
            "Cobertura a comparar:",
            columnas_cobertura
        )

        fig = px.line(
            df_all,
            x='year',
            y=cobertura,
            color='version',
            markers=True,
            title=f"{region_id} – Comparación de {cobertura}",
            template="plotly_white"
        )

        st.plotly_chart(fig, use_container_width=True)

    # ----------------------------------------
    # MODO COMBINADA
    # ----------------------------------------
    elif modo == "Combinada":
        df_long = df_all.melt(
            id_vars=['year', 'version'],
            var_name='Cobertura',
            value_name='Hectáreas'
        )

        fig = px.line(
            df_long,
            x='year',
            y='Hectáreas',
            color='Cobertura',
            line_dash='version',
            title=f"{region_id} – Todas las versiones",
            template="plotly_white"
        )

        st.plotly_chart(fig, use_container_width=True)

    # ----------------------------------------
    # TABLA
    # ----------------------------------------
    with st.expander("📋 Ver tabla de datos"):
        st.dataframe(
            df_all.sort_values(['version', 'year']),
            use_container_width=True
        )
