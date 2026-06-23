"""Pruebas unitarias del script de migración GEE (sin llamadas reales)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.migrar_estadisticas_gee import _normalizar_ruta, listar_assets_en_carpeta


class _FakeEEData:
    pages = [
        {
            "assets": [{"id": "projects/x/parent/A"}, {"id": "projects/x/parent/B"}],
            "nextPageToken": "tok2",
        },
        {
            "assets": [{"id": "projects/x/parent/C"}],
        },
    ]
    calls = 0

    @classmethod
    def listAssets(cls, req):
        page = cls.pages[cls.calls]
        cls.calls += 1
        assert req["parent"] == "projects/x/parent"
        if cls.calls == 2:
            assert req.get("pageToken") == "tok2"
        return page


def test_normalizar_ruta():
    assert _normalizar_ruta(" projects/a/b/ ") == "projects/a/b"


def test_listar_assets_pagina(monkeypatch):
    _FakeEEData.calls = 0
    monkeypatch.setattr(
        "scripts.migrar_estadisticas_gee.ee",
        type("EE", (), {"data": _FakeEEData})(),
    )
    ids = listar_assets_en_carpeta("projects/x/parent/")
    assert ids == [
        "projects/x/parent/A",
        "projects/x/parent/B",
        "projects/x/parent/C",
    ]
