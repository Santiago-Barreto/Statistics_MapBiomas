"""Pruebas de selección de fuente de estadísticas."""

from config import (
    ASSET_PARENT,
    ASSET_PARENT_GENERAL,
    FUENTE_COLECCION,
    FUENTE_GENERAL,
)
from data.stats_source import parent_para_fuente


def test_parent_coleccion_es_mapbiomas():
    assert parent_para_fuente(FUENTE_COLECCION).rstrip("/") == ASSET_PARENT.rstrip("/")


def test_parent_general_es_statistics_general():
    assert (
        parent_para_fuente(FUENTE_GENERAL).rstrip("/")
        == ASSET_PARENT_GENERAL.rstrip("/")
    )


def test_parent_desconocido_cae_a_coleccion():
    assert parent_para_fuente("otra").rstrip("/") == ASSET_PARENT.rstrip("/")


def test_fuente_default_es_general():
    from config import FUENTE_DEFAULT, FUENTE_GENERAL

    assert FUENTE_DEFAULT == FUENTE_GENERAL
    assert parent_para_fuente(FUENTE_DEFAULT).rstrip("/") == ASSET_PARENT_GENERAL.rstrip("/")
