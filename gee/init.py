import ee
import streamlit as st
import json
import os

def inicializar_gee():
    # Si ya está inicializado
    try:
        ee.Number(1).getInfo()
        return
    except Exception:
        pass

    # Detectar Streamlit Cloud (forma segura)
    is_cloud = os.getenv("STREAMLIT_CLOUD") == "true"

    try:
        if is_cloud:
            try:
                secrets = st.secrets
                has_secrets = True
            except Exception:
                has_secrets = False

            if has_secrets and "gcp_service_account" in secrets:
                json_creds = secrets["gcp_service_account"]
                info = json.loads(json_creds)

                credentials = ee.ServiceAccountCredentials(
                    info["client_email"],
                    key_data=json_creds
                )
                ee.Initialize(credentials)
            else:
                raise RuntimeError("Secrets no encontrados en Streamlit Cloud")

        else:
            ee.Initialize()

    except Exception as e:
        st.error(f"❌ Error inicializando GEE: {e}")
        raise
