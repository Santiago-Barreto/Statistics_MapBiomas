"""
Módulo de Autenticación e Inicialización - MapBiomas Colombia
Gestiona la conexión segura con los servidores de Google Earth Engine, 
soportando autenticación por cuenta de servicio o credenciales de usuario.
"""

import ee
import streamlit as st
import json

def inicializar_gee():
    """
    Verifica e inicializa la sesión de Google Earth Engine utilizando 
    credenciales de cuenta de servicio desde secretos de Streamlit o 
    inicialización estándar del entorno.
    """
    try:
        ee.Number(1).getInfo()
        return
    except Exception:
        pass

    json_creds = None
    try:
        if "gcp_service_account" in st.secrets:
            json_creds = st.secrets["gcp_service_account"]
    except Exception:
        pass

    try:
        if json_creds:
            info = json.loads(json_creds)
            credentials = ee.ServiceAccountCredentials(
                info["client_email"],
                key_data=json_creds
            )
            ee.Initialize(credentials)
        else:
            ee.Initialize()
            
    except Exception as e:
        st.error(f"❌ Error de inicialización: {e}")
        st.stop()