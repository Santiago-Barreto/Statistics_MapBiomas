"""
Módulo de Autenticación e Inicialización - MapBiomas Colombia
Gestiona la conexión segura con los servidores de Google Earth Engine, 
soportando autenticación por cuenta de servicio (nube) o credenciales de usuario (local).
"""

import ee
import streamlit as st
import json

def inicializar_gee():
    """
    Verifica e inicializa la sesión de Google Earth Engine.
    
    Busca credenciales en Streamlit Secrets bajo la clave 'gcp_service_account'.
    Si fallan o no existen, intenta la inicialización estándar del entorno.
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
        st.info("💡 Si es local: corre 'earthengine authenticate'. Si es Cloud: configura los Secrets.")
        st.stop()