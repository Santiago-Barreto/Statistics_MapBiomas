"""Tests unitarios del cálculo local de estadísticas (sin GEE)."""

import sqlite3

from scripts.calcular_estadisticas_local import (
    asset_id_stats_local,
    filas_a_stats_rows,
    normalizar_columnas,
    ruta_clasificacion,
    _fc_a_filas,
    _id_columna,
)
from config import ASSET_PARENT, BASE_PATH_V1, BASE_PATH_VX
from tests.conftest import _bootstrap_schema


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


def test_fc_a_filas_con_groups():
    info = {
        "features": [
            {
                "properties": {
                    "year": 2000,
                    "groups": [
                        {"class": 3, "sum": 10.5},
                        {"class": 21, "sum": 2.0},
                    ],
                }
            }
        ]
    }
    filas = _fc_a_filas(info)
    assert filas == [{"year": 2000, "ID03": 10.5, "ID21": 2.0}]


def test_es_solo_estadistica_gee():
    from scripts.calcular_estadisticas_local import _es_solo_estadistica_gee
    from config import ASSET_PARENT, BASE_PATH_VX

    parent = ASSET_PARENT.rstrip("/")
    assert _es_solo_estadistica_gee(f"{parent}/R30484_V7-filtro-espacial")
    assert not _es_solo_estadistica_gee(f"{BASE_PATH_VX.rstrip('/')}/COLOMBIA-30484-7")
    assert not _es_solo_estadistica_gee(parent)
    assert not _es_solo_estadistica_gee(f"{parent}/")


def test_purgar_stats_locales_region_version(tmp_path, monkeypatch):
    from scripts import calcular_estadisticas_local as mod

    db_path = str(tmp_path / "purge_rv.db")
    monkeypatch.setattr("data.db.DB_PATH", db_path)
    conn = sqlite3.connect(db_path)
    _bootstrap_schema(conn)
    parent = ASSET_PARENT.rstrip("/")
    conn.executemany(
        "INSERT INTO assets VALUES (?,?,?,?,?)",
        [
            (f"{parent}/R30484_V7-filtro-espacial", "30484", "Andes", "a", 1),
            (f"{parent}/R30484_V7-old-desc", "30484", "Andes", "b", 1),
            (f"{parent}/R30484_V8-MapaGeneral", "30484", "Andes", "c", 1),
        ],
    )
    conn.execute(
        "INSERT INTO stats VALUES (?,?,?,?)",
        (f"{parent}/R30484_V7-filtro-espacial", 2020, "ID03", 1.0),
    )
    conn.commit()
    conn.close()

    n = mod.purgar_stats_locales_region_version(30484, 7)
    assert n == 2
    conn = sqlite3.connect(db_path)
    left = [r[0] for r in conn.execute("SELECT asset_id FROM assets").fetchall()]
    conn.close()
    assert left == [f"{parent}/R30484_V8-MapaGeneral"]
