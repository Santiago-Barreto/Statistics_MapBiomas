import ee
import streamlit as st
import json

def inicializar_gee():
    try:
        if not ee.data._authorized:
            # Lee el JSON desde los Secrets de Streamlit
            key_dict = json.loads(st.secrets["gcp_service_account"])
            
            # Autentica usando la Service Account
            credentials = ee.ServiceAccountCredentials(
                key_dict['client_email'], 
                key_data=st.secrets["gcp_service_account"]
            )
            ee.Initialize(credentials)
    except Exception as e:
        st.error(f"Error de autenticación GEE: {e}")

def leer_stats_procesadas(nombre_asset):
    inicializar_gee()
    # Ruta base que me diste
    ruta_completa = f"projects/mapbiomas-colombia/assets/CAFE/stat_test/{nombre_asset}"
    
    try:
        # Cargamos la tabla y obtenemos solo las propiedades de cada fila (año)
        fc = ee.FeatureCollection(ruta_completa)
        features = fc.getInfo()['features']
        
        # Extraemos solo el diccionario de datos de cada "feature"
        datos_lista = [f['properties'] for f in features]
        return datos_lista
    except Exception as e:
        raise Exception(f"No se pudo leer el Asset: {e}")
    
def listar_stats_por_region(region_id):
    inicializar_gee()
    parent = 'projects/mapbiomas-colombia/assets/CAFE/stat_test'
    
    try:
        # Listamos todos los assets en esa carpeta
        assets = ee.data.listAssets({'parent': parent})['assets']
        
        # Filtramos los nombres que contengan el ID de la región (ej: "30205")
        nombres = [os.path.basename(a['id']) for a in assets if str(region_id) in a['id']]
        return nombres
    except Exception as e:
        return []