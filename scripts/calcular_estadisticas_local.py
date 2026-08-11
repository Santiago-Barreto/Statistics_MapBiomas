#!/usr/bin/env python3
"""
Cálculo LOCAL de estadísticas Col. 4 (equivalente al tool JS de EXPORT-STATS).

IMPORTANTE — recálculo forzado:
  Aunque la BD local ya tenga R30484_V7-…, la clasificación GEE
  COLOMBIA-30484-7 puede haber cambiado. Por defecto SIEMPRE se vuelve a
  calcular desde la imagen actual y se reemplazan las stats locales de esa
  región+versión (se borran hojas/IDs previos R{reg}_V{ver}* bajo ESTADISTICAS).

- V1 → clasificacion / Vx → clasificacion-ft
- Escribe en SQLite local (y CSV opcional)
- NO hace Export.table.toAsset

Uso (rama local; no pensado para main/Cloud):

    python scripts/calcular_estadisticas_local.py --region 30477 --versions 12
    python scripts/calcular_estadisticas_local.py --desde-asset-final
    python scripts/calcular_estadisticas_local.py --desde-asset-final --dry-run

    # Solo si quieres SALTAR las que ya están (no recomendado si el mapa pudo cambiar):
    python scripts/calcular_estadisticas_local.py --desde-asset-final --solo-faltantes
"""

from __future__ import annotations

import argparse
import csv
import re
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
from data.asset_final import parse_asset_final, leer_asset_final_desde_xlsx  # noqa: E402
from data.db import (  # noqa: E402
    DB_OPERATIONAL_ERRORS,
    get_conn,
    insert_assets_upsert_sql,
    insert_stats_upsert_sql,
    ph,
    with_sqlite_retry,
)
from data.year_norm import normalize_year  # noqa: E402

REINTENTOS = 3
PAUSA_SEG = 0.5


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
    """V1 → clasificacion; V>1 → clasificacion-ft (como el script JS)."""
    base = BASE_PATH_V1 if int(version) == 1 else BASE_PATH_VX
    return f"{base.rstrip('/')}/COLOMBIA-{region_id}-{int(version)}"


def asset_id_stats_local(region_id: int | str, version: int, descripcion: str) -> str:
    """Misma nomenclatura que toAsset del JS, solo como ID local en SQLite."""
    desc = (
        str(descripcion or "sin-descripcion")
        .strip()
        .replace(" ", "-")
        .replace("+", "")
    )
    leaf = f"R{region_id}_V{int(version)}-{desc}" if desc else f"R{region_id}_V{int(version)}"
    return f"{ASSET_PARENT.rstrip('/')}/{leaf}"


def geometria_region(region_id: int | str, regions_asset: str) -> ee.Geometry:
    fc = ee.FeatureCollection(regions_asset).filter(
        ee.Filter.eq("id_regionC", int(region_id))
    )
    return fc.geometry()


def _id_columna(class_id: int) -> str:
    return f"ID{class_id:02d}" if class_id < 100 else f"ID{class_id}"


def calcular_stats_por_anio(
    image: ee.Image,
    region_geo: ee.Geometry,
    years: range,
    scale: int = 30,
) -> list[dict]:
    """
    Área (ha) por clase y año. Un reduceRegion por año (más robusto que un
    getInfo gigante de toda la FeatureCollection).
    """
    bandas = set(image.bandNames().getInfo() or [])
    filas: list[dict] = []

    for y in years:
        band = f"classification_{y}"
        if band not in bandas:
            continue

        img_year = image.select(band).int16().selfMask()
        area_img = ee.Image.pixelArea().divide(1e4).addBands(img_year)
        groups = area_img.reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName="class"),
            geometry=region_geo,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
            tileScale=4,
        ).get("groups")

        raw_groups = None
        for intento in range(REINTENTOS):
            try:
                raw_groups = groups.getInfo()
                break
            except Exception as exc:
                if intento == REINTENTOS - 1:
                    print(f"  ! año {y} falló: {exc}")
                    raw_groups = None
                else:
                    time.sleep(PAUSA_SEG * (intento + 1))

        if not raw_groups:
            continue

        fila: dict = {"year": int(y)}
        for item in raw_groups:
            try:
                cid = int(item["class"])
                area = float(item["sum"])
            except (KeyError, TypeError, ValueError):
                continue
            fila[_id_columna(cid)] = area
        filas.append(fila)

    return filas


def normalizar_columnas(filas: list[dict]) -> list[dict]:
    """Rellena con 0 las clases ausentes en algún año (como el JS)."""
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
            class_id = str(k).split("_")[0]
            try:
                rows.append((asset_id, int(year), class_id, float(v)))
            except (TypeError, ValueError):
                continue
    return rows


def bioma_de_region(region_id: int | str, regions_asset: str) -> str:
    try:
        props = (
            ee.FeatureCollection(regions_asset)
            .filter(ee.Filter.eq("id_regionC", int(region_id)))
            .first()
            .getInfo()
        )
        if props and props.get("properties"):
            return str(props["properties"].get("bioma") or "Sin Bioma")
    except Exception:
        pass
    return "Sin Bioma"


def escribir_sqlite(asset_id: str, region_id: str, bioma: str, filas: list[dict]) -> bool:
    label = asset_id.rsplit("/", 1)[-1]
    ahora = int(time.time())
    stats_rows = filas_a_stats_rows(asset_id, filas)

    def _write():
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                insert_assets_upsert_sql(),
                (asset_id, str(region_id), bioma, label, ahora),
            )
            cur.execute(f"DELETE FROM stats WHERE asset_id = {ph()}", (asset_id,))
            if stats_rows:
                cur.executemany(insert_stats_upsert_sql(), stats_rows)
            conn.commit()
            return True
        except DB_OPERATIONAL_ERRORS:
            conn.rollback()
            return False
        finally:
            conn.close()

    try:
        return bool(with_sqlite_retry(_write))
    except DB_OPERATIONAL_ERRORS:
        return False


def escribir_csv(path: Path, filas: list[dict], meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = ["year"] + sorted(k for k in filas[0] if k != "year") if filas else ["year"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys + ["version", "descripcion", "region_id"])
        w.writeheader()
        for f in filas:
            row = dict(f)
            row.update(meta)
            w.writerow(row)


def existe_stats_en_db(asset_id: str) -> bool:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT 1 FROM stats WHERE asset_id = {ph()} LIMIT 1",
            (asset_id,),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def purgar_stats_locales_region_version(region_id: int | str, version: int) -> int:
    """
    Borra de SQLite cualquier asset/stats local de esa región+versión bajo
    ASSET_PARENT (incluye sufijos viejos si cambió la descripción del mapa).
    """
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


def procesar_uno(
    region_id: int | str,
    version: int,
    *,
    years: range,
    regions_asset: str,
    scale: int,
    dry_run: bool,
    csv_dir: Path | None,
    solo_faltantes: bool,
) -> tuple[bool, str]:
    class_id = ruta_clasificacion(region_id, version)
    print(f"\n=== Región {region_id} V{version}")
    print(f"  clasificación: {class_id}")

    image = ee.Image(class_id)
    try:
        desc = image.get("descripcion").getInfo() or f"v{version}"
    except Exception as exc:
        return False, f"No se pudo leer imagen ({exc})"

    asset_stats = asset_id_stats_local(region_id, version, desc)
    print(f"  stats local ID: {asset_stats}")

    if solo_faltantes and existe_stats_en_db(asset_stats):
        print("  · ya hay stats en BD — omitido (--solo-faltantes)")
        return True, "omitido"

    if dry_run:
        print("  · dry-run: no se calcula ni escribe")
        return True, "dry-run"

    try:
        geo = geometria_region(region_id, regions_asset)
        _ = geo.area(maxError=100).getInfo()
    except Exception as exc:
        return False, f"Región no encontrada / geometría ({exc})"

    # Aunque la BD “crea” tener V7, el mapa GEE pudo cambiar: purgar y recalcular.
    n_old = purgar_stats_locales_region_version(region_id, version)
    if n_old > 0:
        print(f"  · purgadas {n_old} entradas locales previas de R{region_id}_V{version}*")
    print(
        f"  RECALCULANDO desde clasificación actual "
        f"({years.start}–{years.stop - 1}, scale={scale})…"
    )
    t0 = time.time()
    filas = calcular_stats_por_anio(image, geo, years, scale=scale)
    filas = normalizar_columnas(filas)
    print(f"  {len(filas)} años en {time.time() - t0:.1f}s")

    if not filas:
        return False, "sin filas (¿bandas classification_YYYY ausentes?)"

    bioma = bioma_de_region(region_id, regions_asset)
    if not escribir_sqlite(asset_stats, str(region_id), bioma, filas):
        return False, "error escribiendo SQLite"

    if csv_dir is not None:
        out = csv_dir / f"STATS_R{region_id}_V{version}.csv"
        escribir_csv(
            out,
            filas,
            {
                "version": int(version),
                "descripcion": desc,
                "region_id": str(region_id),
            },
        )
        print(f"  CSV → {out}")

    print("  OK → SQLite (stats actualizadas)")
    return True, "ok"


def pares_desde_asset_final() -> list[tuple[str, int]]:
    labels = leer_asset_final_desde_xlsx()
    pares: list[tuple[str, int]] = []
    vistos: set[tuple[str, int]] = set()
    for lab in labels:
        p = parse_asset_final(lab)
        if not p:
            continue
        if p in vistos:
            continue
        vistos.add(p)
        pares.append(p)
    return pares


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Calcula estadísticas Col.4 en local (SQLite/CSV), sin toAsset."
    )
    p.add_argument("--region", type=str, help="ID de región (ej. 30477)")
    p.add_argument(
        "--versions",
        type=str,
        default="",
        help="Versiones separadas por coma (ej. 1,12). Con --region.",
    )
    p.add_argument(
        "--desde-asset-final",
        action="store_true",
        help=f"Procesa todos los pares del Excel de avance ({AVANCE_COLOMBIA_XLSX.name})",
    )
    p.add_argument("--year-min", type=int, default=1985)
    p.add_argument("--year-max", type=int, default=2026)
    p.add_argument("--scale", type=int, default=30)
    p.add_argument(
        "--regions-asset",
        default=ASSET_REGIONES,
        help="FeatureCollection de regiones",
    )
    p.add_argument("--project", default=None, help="GCP project para ee.Initialize")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--solo-faltantes",
        action="store_true",
        help=(
            "NO recomendado si el mapa pudo cambiar: omite región+versión "
            "que ya tengan filas en stats. Por defecto SIEMPRE se recalcula."
        ),
    )
    p.add_argument(
        "--csv-dir",
        type=Path,
        default=None,
        help="Si se indica, también escribe CSV por versión",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    years = range(args.year_min, args.year_max + 1)

    pares: list[tuple[str, int]] = []
    if args.desde_asset_final:
        if not AVANCE_COLOMBIA_XLSX.is_file():
            print(f"No está el Excel de avance: {AVANCE_COLOMBIA_XLSX}", file=sys.stderr)
            return 2
        pares = pares_desde_asset_final()
        print(f"Asset Final: {len(pares)} pares región-versión")
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
            years=years,
            regions_asset=args.regions_asset,
            scale=args.scale,
            dry_run=args.dry_run,
            csv_dir=args.csv_dir,
            solo_faltantes=args.solo_faltantes,
        )
        if msg in ("omitido", "dry-run"):
            skip_n += 1
        elif ok:
            ok_n += 1
        else:
            fail_n += 1
            fallidos.append(f"COLOMBIA-{rid}-{ver}: {msg}")
            print(f"  FAIL: {msg}")

    print("\n========== RESUMEN ==========")
    print(f"OK={ok_n}  omitidos/dry={skip_n}  fallidos={fail_n}")
    for f in fallidos[:40]:
        print(" ", f)
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
