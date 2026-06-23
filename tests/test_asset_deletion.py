"""Pruebas de eliminación segura de assets GEE."""

import sqlite3
import sys
import types
from pathlib import Path

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace()

from config import ASSET_PARENT, BASE_PATH_V1, BASE_PATH_VX
from gee.deletion import (
    clasificacion_desde_estadisticas,
    es_asset_eliminable,
    es_error_asset_inexistente,
    es_ruta_protegida,
    expandir_assets_para_eliminar,
)
from ui.admin import eliminar_assets_seleccionados


STATS_V2 = f"{ASSET_PARENT.rstrip('/')}/R30435_V2"
CLASIF_V2 = f"{BASE_PATH_VX}/COLOMBIA-30435-2"
STATS_V1 = f"{ASSET_PARENT.rstrip('/')}/R30435_V1"
CLASIF_V1 = f"{BASE_PATH_V1}/COLOMBIA-30435-1"


def test_clasificacion_desde_estadisticas_version_2():
    assert clasificacion_desde_estadisticas(STATS_V2) == CLASIF_V2


def test_clasificacion_desde_estadisticas_version_1():
    assert clasificacion_desde_estadisticas(STATS_V1) == CLASIF_V1


def test_expandir_incluye_clasificacion_pareada():
    expandido = expandir_assets_para_eliminar([STATS_V2])
    assert STATS_V2 in expandido
    assert CLASIF_V2 in expandido
    assert len(expandido) == 2


def test_bloquea_carpeta_clasificacion_ft():
    assert es_ruta_protegida(BASE_PATH_VX) is True
    ok, reason = es_asset_eliminable(BASE_PATH_VX)
    assert ok is False
    assert reason is not None
    assert "protegida" in reason.lower()


def test_bloquea_carpeta_clasificacion():
    assert es_ruta_protegida(BASE_PATH_V1) is True
    ok, _ = es_asset_eliminable(BASE_PATH_V1)
    assert ok is False


def test_bloquea_carpeta_estadisticas():
    parent = ASSET_PARENT.rstrip("/")
    assert es_ruta_protegida(parent) is True
    ok, _ = es_asset_eliminable(parent)
    assert ok is False


def test_bloquea_clasificacion_ft_sin_hoja():
    ok, _ = es_asset_eliminable(f"{BASE_PATH_VX}/")
    assert ok is False


def test_permite_asset_clasificacion_especifico():
    ok, reason = es_asset_eliminable(CLASIF_V2)
    assert ok is True
    assert reason is None


def test_permite_asset_estadisticas_especifico():
    ok, reason = es_asset_eliminable(STATS_V2)
    assert ok is True
    assert reason is None


def test_bloquea_v1_en_clasificacion_ft():
    mal = f"{BASE_PATH_VX}/COLOMBIA-30435-1"
    ok, _ = es_asset_eliminable(mal)
    assert ok is False


def test_eliminar_borra_stats_y_clasificacion(monkeypatch, tmp_path: Path):
    db_path = str(tmp_path / "delete_test.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE assets (asset_id TEXT PRIMARY KEY, region_id TEXT, bioma TEXT, label TEXT, last_sync INTEGER)"
    )
    cur.execute(
        "CREATE TABLE stats (asset_id TEXT, year INTEGER, class_id TEXT, area_ha REAL, PRIMARY KEY (asset_id, year, class_id))"
    )
    cur.execute(
        "INSERT INTO assets VALUES (?, ?, ?, ?, ?)",
        (STATS_V2, "30435", "Andes", "R30435_V2", 0),
    )
    cur.execute(
        "INSERT INTO stats VALUES (?, ?, ?, ?)",
        (STATS_V2, 2020, "1", 100.0),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("data.db.DB_PATH", db_path)

    borrados: list[str] = []

    class _FakeEEData:
        @staticmethod
        def deleteAsset(asset_id):
            borrados.append(asset_id)

    monkeypatch.setattr("ui.admin.ee", types.SimpleNamespace(data=_FakeEEData()))

    res = eliminar_assets_seleccionados([STATS_V2])

    assert STATS_V2 in borrados
    assert CLASIF_V2 in borrados
    assert STATS_V2 in res["exitos"]
    assert CLASIF_V2 in res["exitos"]
    assert not res["bloqueados"]

    conn = sqlite3.connect(db_path)
    n_assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    n_stats = conn.execute("SELECT COUNT(*) FROM stats").fetchone()[0]
    conn.close()
    assert n_assets == 0
    assert n_stats == 0


def test_es_error_asset_inexistente():
    assert es_error_asset_inexistente(
        Exception("Asset 'projects/x/COLOMBIA-1' does not exist or doesn't allow this operation.")
    )
    assert not es_error_asset_inexistente(Exception("Permission denied"))


def test_eliminar_continua_si_clasificacion_no_existe(monkeypatch, tmp_path: Path):
    db_path = str(tmp_path / "skip_clasif.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE assets (asset_id TEXT PRIMARY KEY, region_id TEXT, bioma TEXT, label TEXT, last_sync INTEGER)"
    )
    cur.execute(
        "CREATE TABLE stats (asset_id TEXT, year INTEGER, class_id TEXT, area_ha REAL, PRIMARY KEY (asset_id, year, class_id))"
    )
    cur.execute(
        "INSERT INTO assets VALUES (?, ?, ?, ?, ?)",
        (STATS_V2, "30435", "Andes", "R30435_V2", 0),
    )
    cur.execute(
        "INSERT INTO stats VALUES (?, ?, ?, ?)",
        (STATS_V2, 2020, "1", 100.0),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr("data.db.DB_PATH", db_path)

    class _FakeEEData:
        @staticmethod
        def deleteAsset(asset_id):
            if asset_id == CLASIF_V2:
                raise Exception(
                    f"Asset '{asset_id}' does not exist or doesn't allow this operation."
                )

    monkeypatch.setattr("ui.admin.ee", types.SimpleNamespace(data=_FakeEEData()))

    res = eliminar_assets_seleccionados([STATS_V2])

    assert STATS_V2 in res["exitos"]
    assert CLASIF_V2 not in res["exitos"]
    assert not res["errores"]
    assert len(res["omitidos"]) == 1

    conn = sqlite3.connect(db_path)
    n_assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    n_stats = conn.execute("SELECT COUNT(*) FROM stats").fetchone()[0]
    conn.close()
    assert n_assets == 0
    assert n_stats == 0


def test_eliminar_bloquea_carpeta_padre_aunque_se_pase_directamente(monkeypatch, tmp_path: Path):
    db_path = str(tmp_path / "block_parent.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE assets (asset_id TEXT PRIMARY KEY, region_id TEXT, bioma TEXT, label TEXT, last_sync INTEGER)"
    )
    cur.execute(
        "CREATE TABLE stats (asset_id TEXT, year INTEGER, class_id TEXT, area_ha REAL, PRIMARY KEY (asset_id, year, class_id))"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr("data.db.DB_PATH", db_path)

    borrados: list[str] = []

    class _FakeEEData:
        @staticmethod
        def deleteAsset(asset_id):
            borrados.append(asset_id)

    monkeypatch.setattr("ui.admin.ee", types.SimpleNamespace(data=_FakeEEData()))

    res = eliminar_assets_seleccionados([BASE_PATH_VX])

    assert borrados == []
    assert res["exitos"] == []
    assert len(res["bloqueados"]) >= 1
