"""
Eliminación segura de assets en Google Earth Engine.

Solo permite borrar assets hoja concretos (estadísticas por región/versión o
imagen de clasificación COLOMBIA-{región}-{versión}). Bloquea carpetas padre
como clasificacion-ft, clasificacion o la carpeta raíz de estadísticas (ASSET_PARENT).
"""

import re

from config import ASSET_PARENT, BASE_PATH_METADATA, BASE_PATH_V1, BASE_PATH_VX

PROTECTED_EXACT_PATHS = frozenset(
    {
        BASE_PATH_V1.rstrip("/"),
        BASE_PATH_VX.rstrip("/"),
        BASE_PATH_METADATA.rstrip("/"),
        ASSET_PARENT.rstrip("/"),
    }
)

_RE_LEAF_STATS = re.compile(r"^R\d+_V\d+", re.IGNORECASE)
_RE_LEAF_CLASIF_V1 = re.compile(r"^COLOMBIA-\d+-1$", re.IGNORECASE)
_RE_LEAF_CLASIF_VX = re.compile(r"^COLOMBIA-\d+-\d+$", re.IGNORECASE)
_RE_LEAF_METADATA = re.compile(r"^COLOMBIA-\d+-\d+-metadata$", re.IGNORECASE)


def _normalizar_id(asset_id: str) -> str:
    return (asset_id or "").strip().rstrip("/")


def _prefijo_carpeta(base: str) -> str:
    return base.rstrip("/") + "/"


def es_ruta_protegida(asset_id: str) -> bool:
    """True si el ID apunta a una carpeta padre que nunca debe borrarse."""
    aid = _normalizar_id(asset_id)
    if not aid:
        return True
    if aid in PROTECTED_EXACT_PATHS:
        return True
    for protected in PROTECTED_EXACT_PATHS:
        if aid == protected:
            return True
        if aid.endswith("/" + protected.rsplit("/", 1)[-1]) and "COLOMBIA-" not in aid:
            return True
    if aid.endswith("/clasificacion-ft") or aid.endswith("/clasificacion"):
        return True
    if aid.endswith("/metadata"):
        return True
    stats_folder = ASSET_PARENT.rstrip("/").rsplit("/", 1)[-1]
    if aid.endswith(f"/{stats_folder}"):
        return True
    return False


def _es_stats_eliminable(asset_id: str) -> bool:
    prefix = _prefijo_carpeta(ASSET_PARENT)
    if not asset_id.startswith(prefix):
        return False
    leaf = asset_id[len(prefix) :]
    if not leaf or "/" in leaf:
        return False
    return _RE_LEAF_STATS.match(leaf) is not None


def _es_clasificacion_eliminable(asset_id: str) -> bool:
    for base, leaf_re, forbid_v1 in (
        (BASE_PATH_V1, _RE_LEAF_CLASIF_V1, False),
        (BASE_PATH_VX, _RE_LEAF_CLASIF_VX, True),
    ):
        prefix = _prefijo_carpeta(base)
        if not asset_id.startswith(prefix):
            continue
        leaf = asset_id[len(prefix) :]
        if not leaf or "/" in leaf:
            return False
        if not leaf_re.match(leaf):
            return False
        if forbid_v1 and leaf.rsplit("-", 1)[-1] == "1":
            return False
        return True
    return False


def _es_metadata_eliminable(asset_id: str) -> bool:
    prefix = _prefijo_carpeta(BASE_PATH_METADATA)
    if not asset_id.startswith(prefix):
        return False
    leaf = asset_id[len(prefix) :]
    if not leaf or "/" in leaf:
        return False
    return _RE_LEAF_METADATA.match(leaf) is not None


def es_asset_estadisticas(asset_id: str) -> bool:
    """True si el ID es un asset de estadísticas bajo ASSET_PARENT."""
    return _es_stats_eliminable(_normalizar_id(asset_id))


def es_asset_clasificacion(asset_id: str) -> bool:
    """True si el ID es un asset hoja de clasificación COLOMBIA-{región}-{versión}."""
    return _es_clasificacion_eliminable(_normalizar_id(asset_id))


def es_asset_metadata(asset_id: str) -> bool:
    """True si el ID es un asset hoja de metadata COLOMBIA-{región}-{versión}-metadata."""
    return _es_metadata_eliminable(_normalizar_id(asset_id))


def es_asset_opcional(asset_id: str) -> bool:
    """Assets pareados (clasificación o metadata) que pueden no existir."""
    return es_asset_clasificacion(asset_id) or es_asset_metadata(asset_id)


def es_error_asset_inexistente(exc: BaseException) -> bool:
    """True si el error de GEE indica que el asset no existe."""
    msg = str(exc).lower()
    return (
        "does not exist" in msg
        or "doesn't exist" in msg
        or "not found" in msg
        or "no existe" in msg
    )


def es_asset_eliminable(asset_id: str) -> tuple[bool, str | None]:
    """
    Valida si un asset puede eliminarse.

    Returns:
        (True, None) si es seguro borrarlo; (False, motivo) en caso contrario.
    """
    aid = _normalizar_id(asset_id)
    if es_ruta_protegida(aid):
        return False, f"Ruta protegida (carpeta): {aid}"
    if _es_stats_eliminable(aid):
        return True, None
    if _es_clasificacion_eliminable(aid):
        return True, None
    if _es_metadata_eliminable(aid):
        return True, None
    return False, f"Asset fuera de patrón permitido: {aid}"


def clasificacion_desde_estadisticas(stats_asset_id: str) -> str | None:
    """
    Deriva el asset de clasificación asociado a uno de estadísticas.

    Ej.: .../ESTADISTICAS/R30435_V2 -> .../clasificacion-ft/COLOMBIA-30435-2
    """
    label = stats_asset_id.rsplit("/", 1)[-1]
    region_match = re.search(r"R(\d+)", label, re.IGNORECASE)
    version_match = re.search(r"_V(\d+)", label, re.IGNORECASE)
    if not region_match or not version_match:
        return None
    region_id = region_match.group(1)
    version_num = version_match.group(1)
    base = BASE_PATH_V1 if version_num == "1" else BASE_PATH_VX
    return f"{base.rstrip('/')}/COLOMBIA-{region_id}-{version_num}"


def metadata_desde_estadisticas(stats_asset_id: str) -> str | None:
    """
    Deriva el asset de metadata asociado a uno de estadísticas.

    Ej.: .../ESTADISTICAS/R30455_V2 -> .../metadata/COLOMBIA-30455-2-metadata
    """
    label = stats_asset_id.rsplit("/", 1)[-1]
    region_match = re.search(r"R(\d+)", label, re.IGNORECASE)
    version_match = re.search(r"_V(\d+)", label, re.IGNORECASE)
    if not region_match or not version_match:
        return None
    region_id = region_match.group(1)
    version_num = version_match.group(1)
    return f"{BASE_PATH_METADATA.rstrip('/')}/COLOMBIA-{region_id}-{version_num}-metadata"


def expandir_assets_para_eliminar(stats_ids: list[str]) -> list[str]:
    """Incluye los assets de clasificación y metadata pareados por cada versión."""
    resultado: list[str] = []
    visto: set[str] = set()
    for stats_id in stats_ids:
        candidatos = [
            stats_id,
            clasificacion_desde_estadisticas(stats_id),
            metadata_desde_estadisticas(stats_id),
        ]
        for aid in candidatos:
            if not aid:
                continue
            norm = _normalizar_id(aid)
            if norm not in visto:
                visto.add(norm)
                resultado.append(norm)
    return resultado


def describir_plan_eliminacion(stats_ids: list[str]) -> str:
    """Texto legible con las rutas GEE que se intentarán borrar por cada versión."""
    lineas = [
        f"Carpeta estadísticas (GEE + SQLite): {ASSET_PARENT.rstrip('/')}",
        "",
    ]
    for stats_id in stats_ids:
        etiqueta = stats_id.rsplit("/", 1)[-1]
        clasif = clasificacion_desde_estadisticas(stats_id)
        meta = metadata_desde_estadisticas(stats_id)
        lineas.append(f"── {etiqueta} ──")
        lineas.append(f"  Estadísticas:   {stats_id}")
        if clasif:
            lineas.append(f"  Clasificación:  {clasif}")
        else:
            lineas.append("  Clasificación:  (no detectada para este nombre)")
        if meta:
            lineas.append(f"  Metadata:       {meta}")
        else:
            lineas.append("  Metadata:       (no detectada para este nombre)")
        lineas.append("")
    lineas.append(
        "Nota: si la clasificación o la metadata no existen en GEE, se omiten y "
        "se borra solo lo que sí exista (siempre la estadística)."
    )
    return "\n".join(lineas)
