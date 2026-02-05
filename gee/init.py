import ee
import streamlit as st
import json

def inicializar_gee():
    try:
        ee.Number(1).getInfo()
        return
    except Exception:
        pass

    # 1. Intentar obtener credenciales de st.secrets (Cloud)
    json_creds = None
    try:
        if "gcp_service_account" in st.secrets:
            json_creds = st.secrets["gcp_service_account"]
    except Exception:
        # En local, si no hay archivo secrets.toml, st.secrets lanza excepción
        pass

    try:
        if json_creds:
            # Caso: Streamlit Cloud o Local con secrets.toml
            info = json.loads(json_creds)
            credentials = ee.ServiceAccountCredentials(
                info["client_email"],
                key_data=json_creds
            )
            ee.Initialize(credentials)
        else:
            # Caso: Local sin secrets (usa autenticación de gcloud/earthengine)
            ee.Initialize()
            
    except Exception as e:
        st.error(f"❌ Error de inicialización: {e}")
        st.info("💡 Si es local: corre 'earthengine authenticate'. Si es Cloud: configura los Secrets.")
        st.stop()