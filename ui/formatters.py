"""
Módulo de Formateo - MapBiomas Colombia

Normaliza y estandariza la visualización de assets, asegurando 
un orden cronológico basado en versión y tipo de proceso.
"""

import re
from collections import defaultdict


def es_asset_base_sin_proceso(asset_id):
    """
    True si la etiqueta del asset es sólo ``R{id}_V{versión}``
    (mapa base de estadísticas, sin sufijos de proceso).
    """
    label = asset_id.split("/")[-1].replace("-", "_")
    m = re.match(r"^R(\d+)_V(\d+)_?(.*)$", label)
    return bool(m) and (m.group(3) == "")


def efectiva_ultima_version_base(versions):
    """
    Máximo numérico de versión útil entre mapas base.

    En la nomenclatura de assets, ``V11`` no representa la versión revisada más
    reciente cuando conviven varias etiquetas numéricas: si hay otras versiones además del 11,
    se usa el máximo ignorando únicamente a **11** como candidato dominante.

    Cuando sólo existe el 11 para esa región, se conserva igualmente.
    """
    if not versions:
        raise ValueError("lista de versiones vacía")

    uniq = sorted(set(v for v in versions if isinstance(v, int)))

    cand = [v for v in uniq if v != 11]
    return max(cand) if cand else max(uniq)


def seleccionar_assets_base_ultima_version_efectiva(lista_assets):
    """
    Selecciona el asset con la versión más alta para cada región,
    ignorando las versiones V11 y manejando sufijos.
    """
    regiones_dict = {}

    for path in lista_assets:
        nombre = path.split("/")[-1]
        
        match = re.search(r'(R\d+)[_-]V(\d+)', nombre)
        
        if match:
            id_region = match.group(1)
            num_version = int(match.group(2))
            
            if num_version == 11:
                continue
                
            if id_region not in regiones_dict or num_version > regiones_dict[id_region]['version']:
                regiones_dict[id_region] = {
                    'version': num_version,
                    'path': path
                }
    
    return [info['path'] for info in regiones_dict.values()]


def _extraer_clave_orden(asset_id):
    """
    Genera una clave de ordenamiento (Región, Versión, Tipo, Proceso).
    Normaliza separadores para asegurar consistencia en la clasificación.
    """
    label = asset_id.split("/")[-1].replace('-', '_')
    match = re.match(r"R(\d+)_V(\d+)_?(.*)", label)

    if not match:
        return (0, 0, 0, "")

    region = int(match.group(1))
    version = int(match.group(2))
    sufijo = match.group(3).lower()

    es_derivado = 1 if sufijo else 0

    return (region, version, es_derivado, sufijo)


def formatear_nombre_humano(asset_id):
    """
    Transforma IDs técnicos en etiquetas legibles: 'V3 ▹ Mapa General'.
    Soporta separadores mixtos (_ y -).
    """
    label = asset_id.split("/")[-1].replace('-', '_')
    match = re.search(r"_V(\d+)_?(.*)", label)

    if not match:
        return label

    version = match.group(1)
    sufijo = match.group(2)

    if sufijo:
        nombre_proceso = sufijo.replace('_', ' ').title()
        return f"V{version} ▹ {nombre_proceso}"

    return f"V{version} (Base)"


def categorizar_versiones(versiones_list):
    """
    Ordena la lista de assets cronológicamente y los agrupa para el sidebar.
    """
    ordenadas = sorted(versiones_list, key=_extraer_clave_orden)

    return {
        "📋 Secuencia de Procesamiento": ordenadas
    }


def organizar_reporte_novedades(nombres_string):
    """
    Estructura el reporte de nuevos assets organizados por ID de región.
    """
    if not nombres_string:
        return {}

    lista = [n.strip() for n in nombres_string.split(",") if n.strip()]
    reporte = {}

    for nombre in lista:
        label_norm = nombre.replace('-', '_')
        match_reg = re.search(r"R(\d+)", label_norm)
        reg_id = match_reg.group(1) if match_reg else "General"

        reporte.setdefault(reg_id, []).append(
            formatear_nombre_humano(nombre)
        )

    return reporte