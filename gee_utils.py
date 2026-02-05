import ee
import streamlit as st
import json
import os

# -------------------------------------------------
# INICIALIZACIÓN GLOBAL (UNA SOLA VEZ)
# -------------------------------------------------
def inicializar_gee():
    try:
        # Test rápido para saber si ya está inicializado
        ee.Number(1).getInfo()
        return
    except Exception:
        pass

    try:
        if "gcp_service_account" in st.secrets:
            json_creds = st.secrets["gcp_service_account"]
            info = json.loads(json_creds)

            credentials = ee.ServiceAccountCredentials(
                info["client_email"],
                key_data=json_creds
            )

            ee.Initialize(credentials)

        else:
            ee.Initialize()

    except Exception as e:
        st.error(f"Error crítico inicializando GEE: {e}")
        raise


# Inicializar apenas se importa el módulo
inicializar_gee()

# -------------------------------------------------
# LECTURA DE STATS
# -------------------------------------------------
def leer_stats_procesadas(nombre_asset):
    ruta_completa = f"projects/mapbiomas-colombia/assets/CAFE/stat_test/{nombre_asset}"

    try:
        fc = ee.FeatureCollection(ruta_completa)
        features = fc.getInfo().get("features", [])

        if not features:
            return []

        return [f["properties"] for f in features]

    except Exception as e:
        raise Exception(
            f"Error al leer el Asset {nombre_asset}: {str(e)}"
        )


# -------------------------------------------------
# LISTADO DE ASSETS
# -------------------------------------------------
def listar_stats_por_region(region_id):
    parent = "projects/mapbiomas-colombia/assets/CAFE/stat_test"

    try:
        assets_list = ee.data.listAssets({"parent": parent})
        assets = assets_list.get("assets", [])

        return [
            os.path.basename(a["id"])
            for a in assets
            if str(region_id) in a["id"]
        ]

    except Exception as e:
        st.sidebar.error(f"Error listando assets: {e}")
        return []
