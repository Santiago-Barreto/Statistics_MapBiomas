"""
Módulo de persistencia remota - Supabase (Postgres).
Centraliza acceso, sincronización y utilidades de consulta.
"""

import os
from functools import lru_cache
from typing import Iterable

from supabase import Client, create_client


CHUNK_SIZE = 500


def _get_secret(name: str) -> str | None:
    env_value = os.getenv(name)
    if env_value:
        return env_value

    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Retorna un cliente Supabase inicializado por secrets/env."""
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError(
            "Faltan SUPABASE_URL o SUPABASE_ANON_KEY. "
            "Configura estos secretos en Streamlit Cloud."
        )

    return create_client(url, key)


def _chunks(values: Iterable, size: int = CHUNK_SIZE):
    values = list(values)
    for idx in range(0, len(values), size):
        yield values[idx : idx + size]


def inicializar_db():
    """
    Verifica conectividad al backend de Supabase.
    El esquema se gestiona con SQL versionado en `data/supabase_schema.sql`.
    """
    client = get_client()
    client.table("control_sincro").select("id").limit(1).execute()


def obtener_biomas_db() -> list[str]:
    rows = get_client().table("assets").select("bioma").order("bioma").execute().data or []
    biomas = sorted({r.get("bioma") for r in rows if r.get("bioma")})
    return biomas


def obtener_regiones_por_bioma_db(bioma_nombre: str) -> list[str]:
    rows = (
        get_client()
        .table("assets")
        .select("region_id")
        .eq("bioma", bioma_nombre)
        .order("region_id")
        .execute()
        .data
        or []
    )
    regiones = sorted({r.get("region_id") for r in rows if r.get("region_id")})
    return regiones


def listar_versiones_region_db(region_id: str) -> list[str]:
    rows = (
        get_client()
        .table("assets")
        .select("asset_id")
        .eq("region_id", str(region_id))
        .order("asset_id", desc=True)
        .execute()
        .data
        or []
    )
    return [r["asset_id"] for r in rows if r.get("asset_id")]


def listar_assets_bioma_db(bioma_nombre: str) -> list[str]:
    rows = (
        get_client()
        .table("assets")
        .select("asset_id")
        .eq("bioma", bioma_nombre)
        .order("asset_id", desc=True)
        .execute()
        .data
        or []
    )
    return [r["asset_id"] for r in rows if r.get("asset_id")]


def listar_assets_cob_locales_db() -> set[str]:
    rows = get_client().table("assets").select("asset_id").execute().data or []
    return {r["asset_id"] for r in rows if r.get("asset_id")}


def listar_assets_agri_locales_db() -> set[str]:
    rows = get_client().table("stats_agricultura").select("asset_id").execute().data or []
    return {r["asset_id"] for r in rows if r.get("asset_id")}


def leer_stats_db(asset_ids: list[str]) -> list[dict]:
    if not asset_ids:
        return []
    output = []
    for group in _chunks(asset_ids):
        rows = (
            get_client()
            .table("stats")
            .select("asset_id, year, class_id, area_ha")
            .in_("asset_id", group)
            .execute()
            .data
            or []
        )
        output.extend(rows)
    return output


def leer_stats_agri_db(asset_ids: list[str]) -> list[dict]:
    if not asset_ids:
        return []
    output = []
    for group in _chunks(asset_ids):
        rows = (
            get_client()
            .table("stats_agricultura")
            .select("asset_id, year, metric, value")
            .in_("asset_id", group)
            .execute()
            .data
            or []
        )
        output.extend(rows)
    return output


def upsert_assets_db(rows: list[dict]) -> None:
    if not rows:
        return
    for group in _chunks(rows):
        get_client().table("assets").upsert(group, on_conflict="asset_id").execute()


def upsert_stats_db(rows: list[dict]) -> None:
    if not rows:
        return
    for group in _chunks(rows):
        get_client().table("stats").upsert(group, on_conflict="asset_id,year,class_id").execute()


def upsert_stats_agri_db(rows: list[dict]) -> None:
    if not rows:
        return
    for group in _chunks(rows):
        get_client().table("stats_agricultura").upsert(group, on_conflict="asset_id,year,metric").execute()


def borrar_assets_db(asset_ids: list[str]) -> None:
    if not asset_ids:
        return
    for group in _chunks(asset_ids):
        get_client().table("assets").delete().in_("asset_id", group).execute()


def borrar_stats_db(asset_ids: list[str]) -> None:
    if not asset_ids:
        return
    for group in _chunks(asset_ids):
        get_client().table("stats").delete().in_("asset_id", group).execute()


def borrar_stats_agri_db(asset_ids: list[str]) -> None:
    if not asset_ids:
        return
    for group in _chunks(asset_ids):
        get_client().table("stats_agricultura").delete().in_("asset_id", group).execute()


def obtener_resumen_sincro_db() -> tuple[int | None, int, str]:
    rows = (
        get_client()
        .table("control_sincro")
        .select("ultima_fecha, total_nuevos, nombres_nuevos")
        .eq("id", 1)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return (None, 0, "")
    row = rows[0]
    return (
        row.get("ultima_fecha"),
        row.get("total_nuevos", 0) or 0,
        row.get("nombres_nuevos", "") or "",
    )


def guardar_resumen_sincro_db(ultima_fecha: int, total_nuevos: int, nombres_nuevos: str) -> None:
    get_client().table("control_sincro").upsert(
        {
            "id": 1,
            "ultima_fecha": ultima_fecha,
            "total_nuevos": total_nuevos,
            "nombres_nuevos": nombres_nuevos,
        },
        on_conflict="id",
    ).execute()


def try_acquire_sync_lock(owner_id: str, ttl_seconds: int = 90) -> bool:
    res = get_client().rpc(
        "acquire_sync_lock",
        {"p_owner": owner_id, "p_ttl_seconds": ttl_seconds},
    ).execute()
    return bool(res.data)


def release_sync_lock(owner_id: str) -> None:
    get_client().rpc("release_sync_lock", {"p_owner": owner_id}).execute()