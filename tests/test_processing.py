"""Pruebas de carga y agregación de estadísticas locales."""

import pytest

from data.processing import (
    _to_int_year,
    _extraer_region_asset,
    cargar_aportes_regionales_bioma,
    cargar_datos_bioma,
    cargar_datos_agricultura,
    cargar_datos_totales,
)


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
def fake_rows():
    return [
        {"asset_id": "projects/x/R1_V1", "year": 2025, "class_id": "ID03", "area_ha": 10.5},
        {"asset_id": "projects/x/R1_V1", "year": 2026, "class_id": "ID03", "area_ha": 12.0},
        {"asset_id": "projects/x/R1_V1", "year": "no-año", "class_id": "ID03", "area_ha": 1.0},
        {"asset_id": "projects/y/R2_V2", "year": 2026, "class_id": "ID03", "area_ha": 4.0},
    ]


def test_cargar_datos_totales_pivota_y_filtra_anios_invalidos(monkeypatch, fake_rows):
    monkeypatch.setattr("data.processing.leer_stats_db", lambda _asset_ids: fake_rows)
    out = cargar_datos_totales(["projects/x/R1_V1"])

    assert "R1_V1" in out
    df = out["R1_V1"].sort_values("year")
    assert df["year"].tolist() == [2025, 2026]
    assert "ID03" in df.columns
    assert pytest.approx(df.loc[df["year"] == 2026, "ID03"].iloc[0]) == 12.0


def test_cargar_datos_bioma_suma_areas_por_year_class(monkeypatch):
    aid1 = "projects/x/R001_V3"
    aid2 = "projects/y/R002_V3"
    monkeypatch.setattr(
        "data.processing.leer_stats_db",
        lambda _asset_ids: [
            {"asset_id": aid1, "year": 2025, "class_id": "ID03", "area_ha": 100},
            {"asset_id": aid2, "year": 2025, "class_id": "ID03", "area_ha": 50},
            {"asset_id": aid1, "year": 2025, "class_id": "ID49", "area_ha": 7},
            {"asset_id": aid1, "year": 2026, "class_id": "ID03", "area_ha": 10},
        ],
    )

    out = cargar_datos_bioma([aid1, aid2], "Amazónico")

    assert len(out) == 1
    df = next(iter(out.values()))
    row_2025 = df[df["year"] == 2025].iloc[0]
    assert row_2025["ID03"] == 150
    assert row_2025["ID49"] == 7
    assert 2026 not in df["year"].tolist()


def test_cargar_datos_totales_coercion_year_desde_texto_decimal(monkeypatch):
    monkeypatch.setattr(
        "data.processing.leer_stats_db",
        lambda _asset_ids: [
            {"asset_id": "projects/x/Z", "year": "2025.0", "class_id": "ID03", "area_ha": 1.0}
        ],
    )
    out = cargar_datos_totales(["projects/x/Z"])
    assert out["Z"]["year"].tolist() == [2025]


def test_cargar_vacio():
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


def test_cargar_aportes_regionales_bioma_retorna_detalle_por_region(monkeypatch):
    aid1 = "projects/x/R001_V3"
    aid2 = "projects/y/R002_V3"
    monkeypatch.setattr(
        "data.processing.leer_stats_db",
        lambda _asset_ids: [
            {"asset_id": aid1, "year": 2025, "class_id": "ID03", "area_ha": 100},
            {"asset_id": aid2, "year": 2025, "class_id": "ID03", "area_ha": 50},
            {"asset_id": aid1, "year": 2026, "class_id": "ID03", "area_ha": 80},
            {"asset_id": aid2, "year": "no-anio", "class_id": "ID03", "area_ha": 999},
        ],
    )

    out = cargar_aportes_regionales_bioma([aid1, aid2]).sort_values(["region", "year"]).reset_index(drop=True)

    assert out["region"].tolist() == ["R001", "R002"]
    assert out["year"].tolist() == [2025, 2025]
    assert out["class_id"].tolist() == ["ID03", "ID03"]
    assert out["area_ha"].tolist() == [100, 50]


def test_cargar_datos_agricultura_filtra_metricas(monkeypatch):
    monkeypatch.setattr(
        "data.processing.leer_stats_agri_db",
        lambda _asset_ids: [
            {"asset_id": "projects/x/A", "year": 2024, "metric": "regionId", "value": 1},
            {"asset_id": "projects/x/A", "year": 2024, "metric": "yield", "value": 2.5},
        ],
    )

    out = cargar_datos_agricultura(["projects/x/A"])
    assert out is not None
    assert out["metric"].tolist() == ["yield"]
