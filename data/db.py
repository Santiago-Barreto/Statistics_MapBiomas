"""
Módulo de persistencia local - MapBiomas Colombia.
Gestiona la estructura de tablas para metadatos, estadísticas y 
el registro de auditoría de sincronización automática.
"""

import sqlite3
import os
import ee

DB_PATH = "data/mapbiomas.db"

def get_conn():
    """
    Establece la conexión con la base de datos SQLite local.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def inicializar_db():
    """
    Crea el esquema de base de datos. Incluye columnas adicionales en 
    control_sincro para rastrear la cantidad y nombres de nuevos assets.
    """
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        asset_id TEXT PRIMARY KEY,
        region_id TEXT,
        bioma TEXT,
        label TEXT,
        last_sync INTEGER
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        asset_id TEXT,
        year INTEGER,
        class_id TEXT,
        area_ha REAL,
        PRIMARY KEY (asset_id, year, class_id),
        FOREIGN KEY (asset_id) REFERENCES assets (asset_id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_stats_asset_year
    ON stats(asset_id, year)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_assets_bioma_region
    ON assets(bioma, region_id)
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS control_sincro (
        id INTEGER PRIMARY KEY,
        ultima_fecha INTEGER,
        total_nuevos INTEGER,
        nombres_nuevos TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stats_agricultura (
        asset_id TEXT NOT NULL,
        year INTEGER NOT NULL,
        metric TEXT NOT NULL,
        value REAL NOT NULL,
        PRIMARY KEY (asset_id, year, metric),
        FOREIGN KEY (asset_id) REFERENCES assets (asset_id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_agri_asset 
    ON stats_agricultura(asset_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_agri_year 
    ON stats_agricultura(year)
    """)

    
    conn.commit()
    conn.close()