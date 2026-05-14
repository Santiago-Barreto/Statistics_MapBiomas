"""Fixtures para pruebas (BBDD SQLite aislada)."""

import sqlite3

import pytest


@pytest.fixture(autouse=True)
def _tests_usan_sqlite(monkeypatch):
    """Evita que DATABASE_URL del entorno fuerce Postgres en tests."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import data.db as db

    db._database_url_cache = False  # type: ignore[attr-defined]


def _bootstrap_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
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
        CREATE TABLE IF NOT EXISTS assets (
            asset_id TEXT PRIMARY KEY,
            region_id TEXT,
            bioma TEXT,
            label TEXT,
            last_sync INTEGER
        )
        """
    )
    conn.commit()


def insert_stats_rows(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    cur = conn.cursor()
    cur.executemany(
        "INSERT OR REPLACE INTO stats VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
