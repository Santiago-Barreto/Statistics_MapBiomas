"""
Módulo de Gestión de Assets - Agricultura
Utiliza la base de datos local para alimentar la interfaz
con assets que contienen métricas agrícolas procesadas.
"""

from data.db import get_conn


def listar_assets_agricultura():
    """
    Retorna los asset_id que tienen registros en la tabla
    stats_agricultura.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT asset_id
        FROM stats_agricultura
        ORDER BY asset_id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [r[0] for r in rows]


def listar_anios_disponibles(asset_id):
    """
    Retorna los años disponibles para un asset agrícola específico.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT year
        FROM stats_agricultura
        WHERE asset_id = ?
        ORDER BY year ASC
    """, (asset_id,))

    rows = cur.fetchall()
    conn.close()

    return [r[0] for r in rows]


def listar_metricas_disponibles(asset_id):
    """
    Retorna las métricas disponibles para un asset agrícola específico.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT metric
        FROM stats_agricultura
        WHERE asset_id = ?
        ORDER BY metric ASC
    """, (asset_id,))

    rows = cur.fetchall()
    conn.close()

    return [r[0] for r in rows]
