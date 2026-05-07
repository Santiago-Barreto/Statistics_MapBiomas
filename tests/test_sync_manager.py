"""Pruebas de robustez para sincronización con Supabase."""

import sys
import types

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace()

from sync import manager


def test_sincronizar_todo_interno_omite_assets_invalidos(monkeypatch):
    inserted_assets = []

    class _FakeEEData:
        @staticmethod
        def listAssets(payload):
            if payload["parent"] == manager.ASSET_PARENT:
                return {"assets": [{"id": "projects/x/R1_V1"}, {"name": "sin_id"}]}
            return {"assets": [{"name": "sin_id_agri"}]}

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
    monkeypatch.setattr(manager, "listar_assets_cob_locales_db", lambda: set())
    monkeypatch.setattr(manager, "listar_assets_agri_locales_db", lambda: set())
    monkeypatch.setattr(manager, "borrar_stats_db", lambda _ids: None)
    monkeypatch.setattr(manager, "borrar_assets_db", lambda _ids: None)
    monkeypatch.setattr(manager, "borrar_stats_agri_db", lambda _ids: None)
    monkeypatch.setattr(manager, "upsert_assets_db", lambda rows: inserted_assets.extend(rows))
    monkeypatch.setattr(manager, "upsert_stats_db", lambda _rows: None)
    monkeypatch.setattr(manager, "upsert_stats_agri_db", lambda _rows: None)

    total, _nombres = manager.sincronizar_todo_interno()

    assert total == 1
    assert len(inserted_assets) == 1


def test_chequeo_automatico_sincro_adquiere_lock_y_actualiza(monkeypatch):
    monkeypatch.setattr(manager, "obtener_resumen_sincro", lambda: (None, 0, ""))
    monkeypatch.setattr(manager, "obtener_resumen_sincro_db", lambda: (None, 0, ""))
    monkeypatch.setattr(manager, "sincronizar_todo_interno", lambda: (2, "A,B"))
    monkeypatch.setattr(manager, "try_acquire_sync_lock", lambda _owner, ttl_seconds=120: True)
    monkeypatch.setattr(manager, "release_sync_lock", lambda _owner: None)
    saved = {}
    monkeypatch.setattr(
        manager,
        "guardar_resumen_sincro_db",
        lambda ultima_fecha, total, nombres: saved.update(
            {"ultima_fecha": ultima_fecha, "total": total, "nombres": nombres}
        ),
    )

    manager.chequeo_automatico_sincro()

    assert saved["total"] == 2
    assert saved["nombres"] == "A,B"


def test_chequeo_automatico_sincro_sale_si_no_hay_lock(monkeypatch):
    monkeypatch.setattr(manager, "obtener_resumen_sincro", lambda: (None, 0, ""))
    monkeypatch.setattr(manager, "try_acquire_sync_lock", lambda _owner, ttl_seconds=120: False)
    called = {"sync": 0}
    monkeypatch.setattr(manager, "sincronizar_todo_interno", lambda: called.update({"sync": 1}))

    manager.chequeo_automatico_sincro()

    assert called["sync"] == 0
