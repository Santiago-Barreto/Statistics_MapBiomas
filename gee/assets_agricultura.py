"""
Módulo de Gestión de Assets - Agricultura
Utiliza Supabase para alimentar la interfaz
con assets que contienen métricas agrícolas procesadas.
"""

from data.db import get_client


def listar_assets_agricultura():
    """
    Retorna los asset_id que tienen registros en la tabla
    stats_agricultura.
    """
    rows = get_client().table("stats_agricultura").select("asset_id").order("asset_id", desc=True).execute().data or []
    return [r["asset_id"] for r in rows if r.get("asset_id")]


def listar_anios_disponibles(asset_id):
    """
    Retorna los años disponibles para un asset agrícola específico.
    """
    rows = (
        get_client()
        .table("stats_agricultura")
        .select("year")
        .eq("asset_id", asset_id)
        .order("year")
        .execute()
        .data
        or []
    )
    return sorted({r["year"] for r in rows if r.get("year") is not None})


def listar_metricas_disponibles(asset_id):
    """
    Retorna las métricas disponibles para un asset agrícola específico.
    """
    rows = (
        get_client()
        .table("stats_agricultura")
        .select("metric")
        .eq("asset_id", asset_id)
        .order("metric")
        .execute()
        .data
        or []
    )
    return sorted({r["metric"] for r in rows if r.get("metric")})
