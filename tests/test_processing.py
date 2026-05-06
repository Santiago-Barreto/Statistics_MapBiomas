"""Pruebas de carga y agregación de estadísticas locales."""

from pathlib import Path

import pytest

from data.processing import (
    _to_int_year,
    _extraer_region_asset,
    cargar_aportes_regionales_bioma,
    cargar_datos_bioma,
    cargar_datos_totales,
)
from tests.conftest import _bootstrap_schema, insert_stats_rows


@pytest.mark.parametrize(
    "raw,expected",
    [
        (2026, 2026),
        (2026.0, 2026),
        ("2025", 2025),
        ("2026.0", 2026),
        ("", None),
        (None, None),
        ("x", None),
    ],
)
def test_to_int_year(raw, expected):
    assert _to_int_year(raw) == expected


@pytest.fixture
def temp_db(monkeypatch, tmp_path: Path):
    db_path = str(tmp_path / "test_stats.db")
    monkeypatch.setattr("data.db.DB_PATH", db_path)

    conn = sqlite3_connect(db_path)
    _bootstrap_schema(conn)
    conn.close()
    yield db_path


def sqlite3_connect(path: str):
    import sqlite3

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def test_cargar_datos_totales_pivota_y_filtra_anios_invalidos(temp_db):
    conn = sqlite3_connect(temp_db)
    insert_stats_rows(
        conn,
        [
            ("projects/x/R1_V1", 2025, "ID03", 10.5),
            ("projects/x/R1_V1", 2026, "ID03", 12.0),
            ("projects/x/R1_V1", "no-año", "ID03", 1.0),  # se descarta
            ("projects/y/R2_V2", 2026, "ID03", 4.0),
        ],
    )
    conn.close()

    out = cargar_datos_totales(["projects/x/R1_V1"])

    assert "R1_V1" in out
    df = out["R1_V1"].sort_values("year")
    assert df["year"].tolist() == [2025, 2026]
    assert "ID03" in df.columns
    assert pytest.approx(df.loc[df["year"] == 2026, "ID03"].iloc[0]) == 12.0


def test_cargar_datos_bioma_suma_areas_por_year_class(temp_db):
    conn = sqlite3_connect(temp_db)
    aid1 = "projects/x/R001_V3"
    aid2 = "projects/y/R002_V3"
    insert_stats_rows(
        conn,
        [
            (aid1, 2025, "ID03", 100),
            (aid2, 2025, "ID03", 50),
            (aid1, 2025, "ID49", 7),
            (aid1, 2026, "ID03", 10),
        ],
    )
    conn.close()

    out = cargar_datos_bioma([aid1, aid2], "Amazónico")

    assert len(out) == 1
    df = next(iter(out.values()))
    row_2025 = df[df["year"] == 2025].iloc[0]
    assert row_2025["ID03"] == 150
    assert row_2025["ID49"] == 7
    assert 2026 not in df["year"].tolist()


def test_cargar_datos_totales_coercion_year_desde_texto_decimal(temp_db):
    conn = sqlite3_connect(temp_db)
    conn.execute(
        "INSERT OR REPLACE INTO stats VALUES (?,?,?,?)",
        ("projects/x/Z", "2025.0", "ID03", 1.0),
    )
    conn.commit()
    conn.close()

    out = cargar_datos_totales(["projects/x/Z"])
    assert out["Z"]["year"].tolist() == [2025]


def test_cargar_vacio(temp_db):
    assert cargar_datos_totales([]) == {}
    assert cargar_datos_bioma([], "X") == {}


@pytest.mark.parametrize(
    "asset_id,expected",
    [
        ("projects/x/R001_V3", "R001"),
        ("projects/x/r45-v2", "R45"),
        ("projects/x/SIN_REGION", "SIN_REGION"),
    ],
)
def test_extraer_region_asset(asset_id, expected):
    assert _extraer_region_asset(asset_id) == expected


def test_cargar_aportes_regionales_bioma_retorna_detalle_por_region(temp_db):
    conn = sqlite3_connect(temp_db)
    aid1 = "projects/x/R001_V3"
    aid2 = "projects/y/R002_V3"
    insert_stats_rows(
        conn,
        [
            (aid1, 2025, "ID03", 100),
            (aid2, 2025, "ID03", 50),
            (aid1, 2026, "ID03", 80),
            (aid2, "no-anio", "ID03", 999),  # se descarta
        ],
    )
    conn.close()

    out = cargar_aportes_regionales_bioma([aid1, aid2]).sort_values(["region", "year"]).reset_index(drop=True)

    assert out["region"].tolist() == ["R001", "R002"]
    assert out["year"].tolist() == [2025, 2025]
    assert out["class_id"].tolist() == ["ID03", "ID03"]
    assert out["area_ha"].tolist() == [100, 50]
