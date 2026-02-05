import ee
import streamlit as st
import json

def inicializar_gee():
    try:
        ee.Number(1).getInfo()
        return
    except Exception:
        pass

    # Estrategia: Intentar usar secrets primero (Cloud), si falla, usar default (Local)
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
        if "credentials" in str(e).lower() or "authorize" in str(e).lower():
            st.error("❌ Error de Autenticación: Si estás en la nube, configura 'gcp_service_account' en Secrets. Si es local, corre 'earthengine authenticate'.")
        else:
            st.error(f"❌ Error crítico: {e}")
        st.stop()