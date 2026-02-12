"""
Módulo de Formateo - MapBiomas Colombia

Normaliza y estandariza la visualización de assets, asegurando 
un orden cronológico basado en versión y tipo de proceso.
"""

import re

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