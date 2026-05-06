"""Pruebas unitarias para cálculos de visualización en gráficos."""

import pandas as pd

from data.biome_analysis import construir_heatmap_cambios, construir_tabla_linea_temporal


def test_construir_heatmap_cambios_calcula_delta_interanual():
    df = pd.DataFrame(
        [
            {"region": "R001", "year": 2023, "class_id": "ID03", "area_ha": 100},
            {"region": "R001", "year": 2024, "class_id": "ID03", "area_ha": 130},
            {"region": "R001", "year": 2025, "class_id": "ID03", "area_ha": 120},
            {"region": "R002", "year": 2023, "class_id": "ID03", "area_ha": 80},
            {"region": "R002", "year": 2024, "class_id": "ID03", "area_ha": 70},
            {"region": "R002", "year": 2025, "class_id": "ID03", "area_ha": 90},
        ]
    )

    out = construir_heatmap_cambios(df)

    assert out.columns.tolist() == ["2023→2024", "2024→2025"]
    assert out.loc["R001", "2023→2024"] == 30
    assert out.loc["R001", "2024→2025"] == -10
    assert out.loc["R002", "2023→2024"] == -10
    assert out.loc["R002", "2024→2025"] == 20


def test_construir_tabla_linea_temporal_crea_delta_y_sentido():
    df = pd.DataFrame(
        [
            {"region": "R001", "year": 2024, "class_id": "ID03", "area_ha": 100},
            {"region": "R001", "year": 2025, "class_id": "ID03", "area_ha": 85},
            {"region": "R002", "year": 2024, "class_id": "ID03", "area_ha": 20},
            {"region": "R002", "year": 2025, "class_id": "ID03", "area_ha": 50},
        ]
    )

    out = construir_tabla_linea_temporal(df)

    assert out["region"].tolist() == ["R001", "R001", "R002", "R002"]
    assert out["year"].tolist() == [2024, 2025, 2024, 2025]
    assert pd.isna(out.loc[0, "delta_ha"])
    assert out.loc[1, "delta_ha"] == -15
    assert out.loc[3, "delta_ha"] == 30
    assert out["sentido"].tolist() == ["Base", "Pérdida", "Base", "Ganancia"]
