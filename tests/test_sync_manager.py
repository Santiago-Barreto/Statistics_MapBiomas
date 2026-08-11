"""Pruebas de robustez para sincronización y manejo de SQLite."""

import sqlite3
import sys
import types
from pathlib import Path

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace()

from sync import manager


def _crear_schema_basico(path_db: str) -> None:
    conn = sqlite3.connect(path_db)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS assets (
            asset_id TEXT PRIMARY KEY,
            region_id TEXT,
            bioma TEXT,
            label TEXT,
            last_sync INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stats (
            asset_id TEXT,
            year INTEGER,
            class_id TEXT,
            area_ha REAL,
            PRIMARY KEY (asset_id, year, class_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS control_sincro (
            id INTEGER PRIMARY KEY,
            ultima_fecha INTEGER,
            total_nuevos INTEGER,
            nombres_nuevos TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def test_sincronizar_todo_interno_omite_assets_invalidos(monkeypatch, tmp_path: Path):
    db_path = str(tmp_path / "sync_test.db")
    _crear_schema_basico(db_path)
    monkeypatch.setattr("data.db.DB_PATH", db_path)

    class _FakeEEData:
        @staticmethod
        def listAssets(payload):
            if payload["parent"] == manager.ASSET_PARENT:
                return {"assets": [{"id": "projects/x/R1_V1"}, {"name": "sin_id"}]}
            return {"assets": []}

    class _FakeReducer:
        @staticmethod
        def toList():
            class _Repeat:
                @staticmethod
                def repeat(_):
                    return None

            return _Repeat()

    class _FakeFeatureCollection:
        def __init__(self, _):
            pass

        def reduceColumns(self, *_args, **_kwargs):
            class _Result:
                @staticmethod
                def getInfo():
                    return {"list": [["1"], ["Bosque"]]}

            return _Result()

    monkeypatch.setattr(manager.ee, "data", _FakeEEData(), raising=False)
    monkeypatch.setattr(manager.ee, "Reducer", _FakeReducer, raising=False)
    monkeypatch.setattr(manager.ee, "FeatureCollection", _FakeFeatureCollection, raising=False)
    monkeypatch.setattr(manager, "leer_stats_procesadas", lambda _a_id: [])

    total, _nombres, ok = manager.sincronizar_todo_interno()

    conn = sqlite3.connect(db_path)
    total_assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    conn.close()

    assert total == 1
    assert ok is True
    assert total_assets == 1


def test_rellenar_stats_faltantes_desde_gee_inserta_filas(monkeypatch, tmp_path: Path):
    db_path = str(tmp_path / "fill_stats.db")
    _crear_schema_basico(db_path)
    monkeypatch.setattr("data.db.DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO assets VALUES (?, ?, ?, ?, ?)",
        ("projects/test/R30477_V11", "30477", "Andes", "R30477_V11", 0),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        manager,
        "leer_stats_procesadas",
        lambda _aid: [{"year": 2020, "1": 10.5, "system:index": "x"}],
    )

    assert manager.rellenar_stats_faltantes_desde_gee() is True

    conn = sqlite3.connect(db_path)
    n = conn.execute(
        "SELECT COUNT(*) FROM stats WHERE asset_id = ?",
        ("projects/test/R30477_V11",),
    ).fetchone()[0]
    conn.close()
    assert n == 1


def test_chequeo_automatico_sincro_tolera_locked_en_control(monkeypatch):
    monkeypatch.setattr(manager, "obtener_resumen_sincro", lambda: (None, 0, ""))
    monkeypatch.setattr(manager, "sincronizar_todo_interno", lambda: (2, "A,B", True))
    monkeypatch.setattr(manager, "hay_assets_sin_stats", lambda: False)

    class _ConnConBloqueo:
        intentos_global = 0

        def cursor(self):
            return self

        def execute(self, *_args, **_kwargs):
            _ConnConBloqueo.intentos_global += 1
            if _ConnConBloqueo.intentos_global == 1:
                raise sqlite3.OperationalError("database is locked")

        def commit(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr(manager, "get_conn", lambda: _ConnConBloqueo())

    manager.chequeo_automatico_sincro()

    assert _ConnConBloqueo.intentos_global >= 2


def test_purgar_assets_fuera_de_parent(monkeypatch, tmp_path: Path):
    db_path = str(tmp_path / "purge.db")
    _crear_schema_basico(db_path)
    monkeypatch.setattr("data.db.DB_PATH", db_path)

    parent = manager.ASSET_PARENT.rstrip("/")
    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT INTO assets VALUES (?, ?, ?, ?, ?)",
        [
            (f"{parent}/R1_V1", "1", "Andes", "R1_V1", 0),
            ("projects/ee-my-andesnorte/assets/STATISTICS/R1_V1", "1", "Andes", "R1_V1", 0),
        ],
    )
    conn.execute(
        "INSERT INTO stats VALUES (?, ?, ?, ?)",
        ("projects/ee-my-andesnorte/assets/STATISTICS/R1_V1", 2020, "ID03", 1.0),
    )
    conn.commit()
    conn.close()

    n = manager.purgar_assets_fuera_de_parent()
    assert n == 1
    conn = sqlite3.connect(db_path)
    left = [r[0] for r in conn.execute("SELECT asset_id FROM assets").fetchall()]
    n_stats = conn.execute("SELECT COUNT(*) FROM stats").fetchone()[0]
    conn.close()
    assert left == [f"{parent}/R1_V1"]
    assert n_stats == 0


def test_reexportar_todas_estadisticas(monkeypatch, tmp_path: Path):
    db_path = str(tmp_path / "reexport.db")
    _crear_schema_basico(db_path)
    monkeypatch.setattr("data.db.DB_PATH", db_path)

    parent = manager.ASSET_PARENT.rstrip("/")
    aid = f"{parent}/R10_V2"

    class _FakeEEData:
        @staticmethod
        def listAssets(payload):
            if payload["parent"] == manager.ASSET_PARENT:
                return {"assets": [{"id": aid}]}
            return {"assets": []}

    class _FakeReducer:
        @staticmethod
        def toList():
            class _Repeat:
                @staticmethod
                def repeat(_):
                    return None

            return _Repeat()

    class _FakeFeatureCollection:
        def __init__(self, _):
            pass

        def reduceColumns(self, *_args, **_kwargs):
            class _Result:
                def getInfo(self):
                    return {"list": [["10"], ["Andes"]]}

            return _Result()

    monkeypatch.setattr(manager.ee, "data", _FakeEEData)
    monkeypatch.setattr(manager.ee, "Reducer", _FakeReducer)
    monkeypatch.setattr(manager.ee, "FeatureCollection", _FakeFeatureCollection)
    monkeypatch.setattr(
        manager,
        "leer_stats_procesadas",
        lambda _aid: [{"year": 2019, "3": 42.0}],
    )

    # Basura de otro proyecto
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO assets VALUES (?, ?, ?, ?, ?)",
        ("projects/otro/R99_V1", "99", "X", "R99_V1", 0),
    )
    conn.commit()
    conn.close()

    res = manager.reexportar_todas_estadisticas()
    assert res["ok"] is True
    assert res["n_assets"] == 1
    assert res["n_con_stats"] == 1
    assert res["n_purgados"] == 1

    conn = sqlite3.connect(db_path)
    assets = [r[0] for r in conn.execute("SELECT asset_id FROM assets").fetchall()]
    area = conn.execute(
        "SELECT area_ha FROM stats WHERE asset_id = ?", (aid,)
    ).fetchone()[0]
    conn.close()
    assert assets == [aid]
    assert area == 42.0
