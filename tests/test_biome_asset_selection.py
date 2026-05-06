"""Selección de mapas base por región para agregados por bioma."""

import pytest

from ui.formatters import (
    efectiva_ultima_version_base,
    es_asset_base_sin_proceso,
    seleccionar_assets_base_ultima_version_efectiva,
)


@pytest.mark.parametrize(
    "versions,expected",
    [
        ([11], 11),
        ([3, 11], 3),
        ([11, 7, 10], 10),
        ([12, 11], 12),
    ],
)
def test_efectiva_ultima_version_base(versions, expected):
    assert efectiva_ultima_version_base(versions) == expected


def test_es_asset_base_sin_proceso():
    assert es_asset_base_sin_proceso("x/R050_V03")
    assert not es_asset_base_sin_proceso("x/R050_V03_FILTROS")


def test_seleccion_ultimo_base_por_region_excluye_derivados():
    ids = [
        "p/R005_V11",
        "p/R005_V08",
        "p/R005_V08_SEGUIMIENTO",
        "p/R005_V07",
        "p/R010_V03",
    ]
    out = seleccionar_assets_base_ultima_version_efectiva(ids)
    assert set(out) == {"p/R005_V08", "p/R010_V03"}
