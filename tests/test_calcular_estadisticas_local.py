"""Tests unitarios del cálculo local de estadísticas (sin GEE)."""

from scripts.calcular_estadisticas_local import (
    asset_id_stats_local,
    filas_a_stats_rows,
    normalizar_columnas,
    ruta_clasificacion,
    _id_columna,
)
from config import ASSET_PARENT, BASE_PATH_V1, BASE_PATH_VX


def test_ruta_clasificacion_v1_vs_filtros():
    assert ruta_clasificacion(30477, 1).startswith(BASE_PATH_V1.rstrip("/"))
    assert ruta_clasificacion(30477, 1).endswith("COLOMBIA-30477-1")
    assert ruta_clasificacion(30477, 12).startswith(BASE_PATH_VX.rstrip("/"))
    assert ruta_clasificacion(30477, 12).endswith("COLOMBIA-30477-12")


def test_asset_id_stats_local_nomenclatura():
    aid = asset_id_stats_local(30477, 12, "Filtro espacial + frecuencia")
    leaf = aid.rsplit("/", 1)[-1]
    assert aid.startswith(ASSET_PARENT.rstrip("/"))
    assert leaf.startswith("R30477_V12-")
    assert " " not in leaf
    assert "+" not in leaf


def test_id_columna_y_normalizar():
    assert _id_columna(3) == "ID03"
    assert _id_columna(21) == "ID21"
    filas = normalizar_columnas(
        [{"year": 2000, "ID03": 1.0}, {"year": 2001, "ID21": 2.0}]
    )
    assert filas[0]["ID21"] == 0.0
    assert filas[1]["ID03"] == 0.0
    assert filas[1]["ID21"] == 2.0


def test_filas_a_stats_rows():
    rows = filas_a_stats_rows(
        "projects/x/R1_V1",
        [{"year": 2020, "ID03": 10.5, "ID21": 1.0}],
    )
    assert ("projects/x/R1_V1", 2020, "ID03", 10.5) in rows
    assert ("projects/x/R1_V1", 2020, "ID21", 1.0) in rows
