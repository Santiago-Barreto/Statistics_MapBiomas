"""
Módulo de Formateo - MapBiomas Colombia
Gestiona la transformación y agrupación de nombres técnicos para la interfaz.
"""

import re

def formatear_nombre_humano(asset_id):
    """Convierte 'R30205-V3_gapfill' en 'V3 - Gapfill'."""
    label = asset_id.split('/')[-1]
    match = re.search(r"-(V\d+.*)", label)
    if match:
        return match.group(1).replace('_', ' - ').replace('-', ' ').title()
    return label

def categorizar_versiones(versiones_list):
    """Agrupa assets por etapa técnica para los checkboxes del sidebar."""
    categorias = {
        "🚀 Clasificación & Joins": [],
        "🛠️ Refinamiento (Gapfill/Temp)": [],
        "🧪 Filtros & Ajustes": [],
        "✅ Mapas Finales/Generales": []
    }
    for v in versiones_list:
        v_l = v.lower()
        if "mapageneral" in v_l: categorias["✅ Mapas Finales/Generales"].append(v)
        elif "filtro" in v_l: categorias["🧪 Filtros & Ajustes"].append(v)
        elif "gapfill" in v_l or "temporal" in v_l: categorias["🛠️ Refinamiento (Gapfill/Temp)"].append(v)
        else: categorias["🚀 Clasificación & Joins"].append(v)
    return categorias

def organizar_reporte_novedades(nombres_string):
    """
    Toma la cadena 'R30205-V1, R30424-V2...' y la organiza por Región.
    """
    if not nombres_string: return {}
    
    lista = [n.strip() for n in nombres_string.split(",")]
    reporte = {}
    
    for nombre in lista:
        match_reg = re.search(r"R(\d+)", nombre)
        reg_id = match_reg.group(1) if match_reg else "Otras"
        
        if reg_id not in reporte:
            reporte[reg_id] = []
        
        reporte[reg_id].append(formatear_nombre_humano(nombre))
        
    return reporte