#!/usr/bin/env python3
"""
Cálculo de estadísticas Col. 4 — mismo flujo que el tool JS EXPORT-STATS.

NO usa getInfo() para el reduceRegion (eso se cuelga). Hace:

  1) FeatureCollection server-side (calculateStats + ceros), igual que el JS
  2) ee.batch.Export.table.toAsset → ESTADISTICAS (tarea async en GEE)
  3) Espera la tarea
  4) Lee el asset y lo vuelca a SQLite local

Uso (rama local):

    python scripts/calcular_estadisticas_local.py --region 30477 --versions 12
    python scripts/calcular_estadisticas_local.py --desde-asset-final
    python scripts/calcular_estadisticas_local.py --desde-asset-final --dry-run

    # Solo lanza Exports (como el Code Editor) y no espera / no escribe SQLite:
    python scripts/calcular_estadisticas_local.py --desde-asset-final --solo-lanzar
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ee  # noqa: E402

from config import (  # noqa: E402
    ASSET_PARENT,
    ASSET_REGIONES,
    AVANCE_COLOMBIA_XLSX,
    BASE_PATH_V1,
    BASE_PATH_VX,
)
from data.asset_final import leer_asset_final_desde_xlsx, parse_asset_final  # noqa: E402
from data.db import (  # noqa: E402
    DB_OPERATIONAL_ERRORS,
    get_conn,
    insert_assets_upsert_sql,
    insert_stats_upsert_sql,
    ph,
    with_sqlite_retry,
)
from data.year_norm import normalize_year  # noqa: E402
from gee.assets import leer_stats_procesadas  # noqa: E402
from sync.manager import _construir_rows_stats  # noqa: E402

PAUSA_POLL_SEG = 20


def inicializar_ee(project: str | None = None) -> None:
    try:
        ee.Number(1).getInfo()
        return
    except Exception:
        pass
    if project:
        ee.Initialize(project=project)
    else:
        ee.Initialize()


def ruta_clasificacion(region_id: int | str, version: int) -> str:
    base = BASE_PATH_V1 if int(version) == 1 else BASE_PATH_VX
    return f"{base.rstrip('/')}/COLOMBIA-{region_id}-{int(version)}"


def normalizar_descripcion(desc: str) -> str:
    return str(desc or "sin-descripcion").strip().replace(" ", "-").replace("+", "")


def asset_id_stats(region_id: int | str, version: int, descripcion: str) -> str:
    """Igual que assetId del Export.toAsset del JS."""
    leaf = f"R{region_id}_V{int(version)}-{normalizar_descripcion(descripcion)}"
    return f"{ASSET_PARENT.rstrip('/')}/{leaf}"


def region_feature(region_id: int | str, regions_asset: str) -> ee.FeatureCollection:
    return ee.FeatureCollection(regions_asset).filter(
        ee.Filter.eq("id_regionC", int(region_id))
    )


def calculate_stats(
    image: ee.Image,
    region_geo: ee.Geometry,
    version_val: int,
    version_desc: ee.ComputedObject,
    year_min: int,
    year_max: int,
    scale: int = 30,
) -> ee.FeatureCollection:
    """
    Réplica de calculateStats del JS (reduceRegion + IDxx planos).
    No se evalúa aquí: solo se construye el grafo para Export.
    """
    years_process = ee.List.sequence(year_min, year_max)
    img = image
    geo = region_geo
    ver = ee.Number(int(version_val))
    desc = version_desc
    sc = int(scale)

    def _por_anio(y):
        year = ee.Number(y).format("%d")
        band_name = ee.String("classification_").cat(year)

        def _calc():
            img_year = img.select([band_name]).int16().selfMask()
            area_img = ee.Image.pixelArea().divide(1e4).addBands(img_year)
            groups = area_img.reduceRegion(
                reducer=ee.Reducer.sum().group(groupField=1, groupName="class"),
                geometry=geo,
                scale=sc,
                maxPixels=1e13,
            ).get("groups")
            groups_list = ee.List(groups)
            base_dict = ee.Dictionary(
                {
                    "year": year,
                    "version": ver,
                    "descripcion": desc,
                }
            )

            def _iter(item, memo):
                item = ee.Dictionary(item)
                class_id = ee.Number(item.get("class")).toInt()
                area = item.get("sum")
                class_str = ee.String(class_id)
                col_name = ee.Algorithms.If(
                    class_id.lt(10),
                    ee.String("ID0").cat(class_str),
                    ee.String("ID").cat(class_str),
                )
                return ee.Dictionary(memo).set(col_name, area)

            class_dict = groups_list.iterate(_iter, base_dict)
            return ee.Feature(ee.Geometry.Point([0, 0]), class_dict)

        return ee.Algorithms.If(img.bandNames().contains(band_name), _calc(), None)

    return ee.FeatureCollection(years_process.map(_por_anio, True))


def normalizar_fc_ceros(fc_raw: ee.FeatureCollection) -> ee.FeatureCollection:
    """Relleno de ceros por columna (pasos 4.3 A–C del JS)."""
    all_keys = (
        fc_raw.map(lambda f: f.set("keys_list", f.propertyNames()))
        .aggregate_array("keys_list")
        .flatten()
        .distinct()
        .removeAll(["year", "version", "descripcion", "system:index"])
    )
    zero_list = ee.List.repeat(0, all_keys.length())
    zero_dict = ee.Dictionary.fromLists(all_keys, zero_list)

    def _fill(f):
        full = zero_dict.combine(f.toDictionary(), True)
        return ee.Feature(ee.Geometry.Point([0, 0]), full)

    return fc_raw.map(_fill)


def borrar_asset_si_existe(asset_id: str) -> None:
    try:
        ee.data.deleteAsset(asset_id)
        print(f"  · asset GEE previo borrado: {asset_id.rsplit('/', 1)[-1]}", flush=True)
    except Exception:
        pass


def esperar_tarea(task: ee.batch.Task, etiqueta: str) -> bool:
    """Espera Export async (como Tasks del Code Editor)."""
    print(f"  · tarea GEE iniciada [{etiqueta}] id={task.id}", flush=True)
    while True:
        status = task.status()
        state = status.get("state")
        if state == "COMPLETED":
            print(f"  · COMPLETED [{etiqueta}]", flush=True)
            return True
        if state in ("FAILED", "CANCELLED"):
            print(
                f"  · {state} [{etiqueta}]: {status.get('error_message')}",
                flush=True,
            )
            return False
        print(f"  · {state}… esperando {PAUSA_POLL_SEG}s", flush=True)
        time.sleep(PAUSA_POLL_SEG)


def bioma_de_region(region_id: int | str, regions_asset: str) -> str:
    try:
        props = (
            region_feature(region_id, regions_asset).first().getInfo() or {}
        ).get("properties") or {}
        return str(props.get("bioma") or "Sin Bioma")
    except Exception:
        return "Sin Bioma"


def purgar_stats_locales_region_version(region_id: int | str, version: int) -> int:
    prefijo = ASSET_PARENT.rstrip("/") + "/"
    patrones = [
        f"{prefijo}R{region_id}_V{int(version)}%",
        f"{prefijo}R{region_id}-V{int(version)}%",
    ]

    def _borrar():
        from data.db import ph_join

        conn = get_conn()
        try:
            cur = conn.cursor()
            ids: list[str] = []
            for pat in patrones:
                cur.execute(
                    f"SELECT asset_id FROM assets WHERE asset_id LIKE {ph()}",
                    (pat,),
                )
                ids.extend(r[0] for r in cur.fetchall())
            ids = list(dict.fromkeys(ids))
            if not ids:
                return 0
            phs = ph_join(len(ids))
            cur.execute(f"DELETE FROM stats WHERE asset_id IN ({phs})", ids)
            cur.execute(f"DELETE FROM assets WHERE asset_id IN ({phs})", ids)
            conn.commit()
            return len(ids)
        except DB_OPERATIONAL_ERRORS:
            conn.rollback()
            return -1
        finally:
            conn.close()

    try:
        return int(with_sqlite_retry(_borrar))
    except DB_OPERATIONAL_ERRORS:
        return -1


def escribir_sqlite_desde_gee_asset(
    asset_id: str, region_id: str, bioma: str
) -> tuple[bool, int]:
    raw = leer_stats_procesadas(asset_id)
    if not raw:
        return False, 0
    rows = _construir_rows_stats(asset_id, raw)
    label = asset_id.rsplit("/", 1)[-1]
    ahora = int(time.time())

    def _write():
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                insert_assets_upsert_sql(),
                (asset_id, str(region_id), bioma, label, ahora),
            )
            cur.execute(f"DELETE FROM stats WHERE asset_id = {ph()}", (asset_id,))
            if rows:
                cur.executemany(insert_stats_upsert_sql(), rows)
            conn.commit()
            return True
        except DB_OPERATIONAL_ERRORS:
            conn.rollback()
            return False
        finally:
            conn.close()

    try:
        ok = bool(with_sqlite_retry(_write))
    except DB_OPERATIONAL_ERRORS:
        return False, 0
    return ok, len(rows)


def lanzar_export(
    fc: ee.FeatureCollection,
    description: str,
    asset_id: str,
) -> ee.batch.Task:
    """Igual que Export.table.toAsset del JS."""
    task = ee.batch.Export.table.toAsset(
        collection=fc,
        description=description[:100],
        assetId=asset_id,
    )
    task.start()
    return task


def procesar_uno(
    region_id: int | str,
    version: int,
    *,
    year_min: int,
    year_max: int,
    regions_asset: str,
    scale: int,
    dry_run: bool,
    solo_lanzar: bool,
    limpiar_asset: bool,
) -> tuple[bool, str]:
    class_path = ruta_clasificacion(region_id, version)
    print(f"\n=== Región {region_id} V{version}", flush=True)
    print(f"  clasificación: {class_path}", flush=True)

    image = ee.Image(class_path)
    try:
        # Único getInfo ligero (como nameDescript = descServer.getInfo() en el JS)
        desc = image.get("descripcion").getInfo() or f"v{version}"
    except Exception as exc:
        return False, f"No se pudo leer imagen/descripcion ({exc})"

    asset_stats = asset_id_stats(region_id, version, desc)
    file_name = f"STATS_R{region_id}_V{version}"
    asset_desc = asset_stats.rsplit("/", 1)[-1]
    print(f"  asset ESTADISTICAS: {asset_stats}", flush=True)

    if dry_run:
        print("  · dry-run: no se lanza Export", flush=True)
        return True, "dry-run"

    region_fc = region_feature(region_id, regions_asset)
    region_geo = region_fc.geometry()

    # Grafo server-side (sin evaluar reduceRegion en el cliente)
    desc_ee = image.get("descripcion")
    fc_raw = calculate_stats(
        image, region_geo, int(version), desc_ee, year_min, year_max, scale=scale
    )
    fc_stats = normalizar_fc_ceros(fc_raw)

    # Recalcular: borrar asset GEE previo si existe (toAsset falla si ya está)
    borrar_asset_si_existe(asset_stats)
    n_old = purgar_stats_locales_region_version(region_id, version)
    if n_old > 0:
        print(f"  · purgadas {n_old} entradas locales previas", flush=True)

    print("  · lanzando Export.table.toAsset (async GEE)…", flush=True)
    try:
        task = lanzar_export(fc_stats, asset_desc or file_name, asset_stats)
    except Exception as exc:
        return False, f"No se pudo iniciar Export ({exc})"

    if solo_lanzar:
        print("  · --solo-lanzar: no se espera ni escribe SQLite", flush=True)
        return True, "lanzado"

    if not esperar_tarea(task, asset_desc):
        return False, "Export falló"

    bioma = bioma_de_region(region_id, regions_asset)
    ok, n_rows = escribir_sqlite_desde_gee_asset(asset_stats, str(region_id), bioma)
    if not ok:
        return False, "Export OK pero no se pudo leer/escribir en SQLite"

    if limpiar_asset:
        borrar_asset_si_existe(asset_stats)
        print("  · asset GEE eliminado tras volcar a SQLite", flush=True)

    print(f"  OK → SQLite ({n_rows} filas)", flush=True)
    return True, "ok"


def pares_desde_asset_final() -> list[tuple[str, int]]:
    labels = leer_asset_final_desde_xlsx()
    pares: list[tuple[str, int]] = []
    vistos: set[tuple[str, int]] = set()
    for lab in labels:
        p = parse_asset_final(lab)
        if not p or p in vistos:
            continue
        vistos.add(p)
        pares.append(p)
    return pares


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Stats Col.4 como el JS: Export.table.toAsset async → SQLite. "
            "No usa getInfo del reduceRegion."
        )
    )
    p.add_argument("--region", type=str)
    p.add_argument("--versions", type=str, default="")
    p.add_argument("--desde-asset-final", action="store_true")
    p.add_argument("--year-min", type=int, default=1985)
    p.add_argument("--year-max", type=int, default=2026)
    p.add_argument("--scale", type=int, default=30)
    p.add_argument("--regions-asset", default=ASSET_REGIONES)
    p.add_argument("--project", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--solo-lanzar",
        action="store_true",
        help="Solo arranca Exports en GEE (rápido); no espera ni escribe SQLite",
    )
    p.add_argument(
        "--limpiar-asset",
        action="store_true",
        help="Tras volcar a SQLite, borra el asset en ESTADISTICAS",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.desde_asset_final:
        if not AVANCE_COLOMBIA_XLSX.is_file():
            print(f"No está el Excel: {AVANCE_COLOMBIA_XLSX}", file=sys.stderr)
            return 2
        pares = pares_desde_asset_final()
        print(f"Asset Final: {len(pares)} pares región-versión", flush=True)
    elif args.region and args.versions:
        vers = [int(x.strip()) for x in args.versions.split(",") if x.strip()]
        pares = [(str(args.region), v) for v in vers]
    else:
        print("Indica --desde-asset-final o --region y --versions", file=sys.stderr)
        return 2

    inicializar_ee(args.project)

    ok_n = fail_n = skip_n = 0
    fallidos: list[str] = []
    for rid, ver in pares:
        ok, msg = procesar_uno(
            rid,
            ver,
            year_min=args.year_min,
            year_max=args.year_max,
            regions_asset=args.regions_asset,
            scale=args.scale,
            dry_run=args.dry_run,
            solo_lanzar=args.solo_lanzar,
            limpiar_asset=args.limpiar_asset,
        )
        if msg in ("dry-run", "lanzado"):
            skip_n += 1
        elif ok:
            ok_n += 1
        else:
            fail_n += 1
            fallidos.append(f"COLOMBIA-{rid}-{ver}: {msg}")
            print(f"  FAIL: {msg}", flush=True)

    print("\n========== RESUMEN ==========", flush=True)
    print(f"OK={ok_n}  lanzados/dry={skip_n}  fallidos={fail_n}", flush=True)
    for f in fallidos[:40]:
        print(" ", f, flush=True)
    return 0 if fail_n == 0 else 1


# --- helpers usados por tests unitarios ---
def asset_id_stats_local(region_id, version, descripcion):
    return asset_id_stats(region_id, version, descripcion)


def _id_columna(class_id: int) -> str:
    return f"ID{class_id:02d}" if class_id < 100 else f"ID{class_id}"


def normalizar_columnas(filas: list[dict]) -> list[dict]:
    keys: set[str] = set()
    for f in filas:
        keys.update(k for k in f if k != "year")
    out = []
    for f in filas:
        full = {k: 0.0 for k in keys}
        full.update(f)
        full["year"] = int(f["year"])
        out.append(full)
    return out


def filas_a_stats_rows(asset_id: str, filas: list[dict]) -> list[tuple]:
    rows = []
    for f in filas:
        year = normalize_year(f.get("year"))
        if year is None:
            continue
        for k, v in f.items():
            if k == "year":
                continue
            try:
                rows.append((asset_id, int(year), str(k).split("_")[0], float(v)))
            except (TypeError, ValueError):
                continue
    return rows


def _fc_a_filas(fc_info: dict) -> list[dict]:
    """Compat tests: propiedades IDxx o groups."""
    filas = []
    for feat in fc_info.get("features") or []:
        props = feat.get("properties") or {}
        year = normalize_year(props.get("year"))
        if year is None:
            continue
        if props.get("groups") is not None:
            fila = {"year": int(year)}
            for item in props["groups"]:
                try:
                    fila[_id_columna(int(item["class"]))] = float(item["sum"])
                except (KeyError, TypeError, ValueError):
                    continue
            if len(fila) > 1:
                filas.append(fila)
            continue
        fila = {"year": int(year)}
        for k, v in props.items():
            if str(k).upper().startswith("ID"):
                try:
                    fila[str(k)] = float(v)
                except (TypeError, ValueError):
                    continue
        if len(fila) > 1:
            filas.append(fila)
    return filas


if __name__ == "__main__":
    raise SystemExit(main())
