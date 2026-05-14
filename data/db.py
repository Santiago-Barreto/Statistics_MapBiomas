"""
Módulo de persistencia - MapBiomas Colombia.

Modo SQLite (por defecto): archivo data/mapbiomas.db.

Modo PostgreSQL (Neon u otro): definir DATABASE_URL en variables de entorno
o en Streamlit Secrets (.streamlit/secrets.toml en local, Secrets en Cloud).
Ejemplo Neon: postgresql://user:pass@host/db?sslmode=require
"""

import os
import sqlite3

# Ruta absoluta estable para SQLite cuando no hay DATABASE_URL
DB_PATH = os.path.join(os.path.dirname(__file__), "mapbiomas.db")

_ERR = [sqlite3.OperationalError]
try:
    import psycopg2

    _ERR.append(psycopg2.OperationalError)
except ImportError:
    psycopg2 = None  # type: ignore

DB_OPERATIONAL_ERRORS = tuple(_ERR)

_database_url_cache: str | None | bool = False


def _resolve_database_url() -> str | None:
    """URL de Postgres (Neon). None = usar SQLite."""
    global _database_url_cache
    if _database_url_cache is not False:
        return _database_url_cache if _database_url_cache else None

    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        _database_url_cache = url
        return url

    try:
        import streamlit as st

        if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
            u = str(st.secrets["DATABASE_URL"]).strip()
            if u:
                _database_url_cache = u
                return u
    except Exception:
        pass

    _database_url_cache = None
    return None


def is_postgres() -> bool:
    return _resolve_database_url() is not None


def ph() -> str:
    """Placeholder posicional para la capa activa (%s Postgres, ? SQLite)."""
    return "%s" if is_postgres() else "?"


def ph_join(n: int) -> str:
    return ",".join([ph()] * n)


def insert_assets_upsert_sql() -> str:
    if is_postgres():
        p = ph()
        return (
            f"INSERT INTO assets (asset_id, region_id, bioma, label, last_sync) "
            f"VALUES ({p}, {p}, {p}, {p}, {p}) "
            "ON CONFLICT (asset_id) DO UPDATE SET "
            "region_id = EXCLUDED.region_id, bioma = EXCLUDED.bioma, "
            "label = EXCLUDED.label, last_sync = EXCLUDED.last_sync"
        )
    return "INSERT OR REPLACE INTO assets VALUES (?, ?, ?, ?, ?)"


def insert_stats_upsert_sql() -> str:
    if is_postgres():
        p = ph()
        return (
            f"INSERT INTO stats (asset_id, year, class_id, area_ha) "
            f"VALUES ({p}, {p}, {p}, {p}) "
            "ON CONFLICT (asset_id, year, class_id) DO UPDATE SET "
            "area_ha = EXCLUDED.area_ha"
        )
    return "INSERT OR REPLACE INTO stats VALUES (?, ?, ?, ?)"


def upsert_control_sincro_sql() -> str:
    if is_postgres():
        p = ph()
        return (
            f"INSERT INTO control_sincro (id, ultima_fecha, total_nuevos, nombres_nuevos) "
            f"VALUES (1, {p}, {p}, {p}) "
            "ON CONFLICT (id) DO UPDATE SET "
            "ultima_fecha = EXCLUDED.ultima_fecha, "
            "total_nuevos = EXCLUDED.total_nuevos, "
            "nombres_nuevos = EXCLUDED.nombres_nuevos"
        )
    return """
        INSERT OR REPLACE INTO control_sincro (id, ultima_fecha, total_nuevos, nombres_nuevos)
        VALUES (1, ?, ?, ?)
    """


def get_conn():
    """
    Conexión SQLite o PostgreSQL según DATABASE_URL.
    """
    url = _resolve_database_url()
    if url:
        if psycopg2 is None:
            raise RuntimeError(
                "DATABASE_URL está definido pero psycopg2 no está instalado. "
                "Añade psycopg2-binary a requirements.txt."
            )
        return psycopg2.connect(url)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def inicializar_db():
    """
    Crea el esquema en SQLite o PostgreSQL.
    """
    conn = get_conn()
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

    if is_postgres():
        cur.execute(
            """
    CREATE TABLE IF NOT EXISTS stats (
        asset_id TEXT,
        year INTEGER,
        class_id TEXT,
        area_ha DOUBLE PRECISION,
        PRIMARY KEY (asset_id, year, class_id),
        FOREIGN KEY (asset_id) REFERENCES assets (asset_id) ON DELETE CASCADE
    )
    """
        )
    else:
        cur.execute(
            """
    CREATE TABLE IF NOT EXISTS stats (
        asset_id TEXT,
        year INTEGER,
        class_id TEXT,
        area_ha REAL,
        PRIMARY KEY (asset_id, year, class_id),
        FOREIGN KEY (asset_id) REFERENCES assets (asset_id) ON DELETE CASCADE
    )
    """
        )

    cur.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_stats_asset_year
    ON stats(asset_id, year)
    """
    )

    cur.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_assets_bioma_region
    ON assets(bioma, region_id)
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
