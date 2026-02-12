"""
Módulo de Formateo - MapBiomas Colombia
Gestiona la transformación y orden cronológico de nombres técnicos con estética profesional.
"""

import re


def _extraer_clave_orden(asset_id):
    """
    Retorna (region:int, version:int, es_derivado:int, sufijo:str) para orden cronológico.
    """
    label = asset_id.split("/")[-1]
    match = re.match(r"R(\d+)-V(\d+)_?(.*)", label)

    if not match:
        return (0, 0, 0, "")

    region = int(match.group(1))
    version = int(match.group(2))
    sufijo = match.group(3).lower()

    # Priorizamos la versión base (0) sobre los derivados (1) como gapfill/filtros
    es_derivado = 1 if sufijo else 0

    return (region, version, es_derivado, sufijo)


def formatear_nombre_humano(asset_id):
    """
    Convierte 'R30205-V3_gapfill' en 'V3 ▹ Gapfill'
    """
    label = asset_id.split("/")[-1]
    match = re.search(r"-V(\d+)_?(.*)", label)

    if not match:
        return f"📦 {label}"

    version = match.group(1)
    sufijo = match.group(2)

    if sufijo:
        # Usamos un marcador sutil (▹) para procesos derivados
        nombre_proceso = sufijo.replace('_', ' ').title()
        return f"V{version} ▹ {nombre_proceso}"

    return f"V{version} (Base)"


def categorizar_versiones(versiones_list):
    """
    Ordena cronológicamente y devuelve el grupo de procesamiento.
    """
    ordenadas = sorted(versiones_list, key=_extraer_clave_orden)

    return {
        "📋 Flujo de Trabajo": ordenadas
    }


def organizar_reporte_novedades(nombres_string):
    """
    Organiza la cadena de assets nuevos por Región con iconos de ubicación.
    """
    if not nombres_string:
        return {}

    lista = [n.strip() for n in nombres_string.split(",") if n.strip()]
    reporte = {}

    for nombre in lista:
        match_reg = re.search(r"R(\d+)", nombre)
        reg_id = match_reg.group(1) if match_reg else "General"

        # Agregamos el icono de pin para las regiones en el reporte
        reporte.setdefault(reg_id, []).append(
            formatear_nombre_humano(nombre)
        )

    return reporte