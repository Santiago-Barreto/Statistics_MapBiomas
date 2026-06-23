#!/usr/bin/env python3
"""
Copia assets de estadísticas entre carpetas/proyectos GEE.

Uso típico (desde la raíz del repo):

    python scripts/migrar_estadisticas_gee.py --dry-run
    python scripts/migrar_estadisticas_gee.py --project ee-my-andesnorte

Requiere: earthengine authenticate y permisos de lectura en origen
y escritura en destino.
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

from config import ASSET_PARENT  # noqa: E402

ORIGEN_DEFAULT = "projects/mapbiomas-colombia/assets/LULC/COLECCION4/ESTADISTICAS"
DESTINO_DEFAULT = ASSET_PARENT.rstrip("/")

REINTENTOS = 3
PAUSA_BASE_SEG = 1.0
PAUSA_ENTRE_COPIAS_SEG = 0.25


def _normalizar_ruta(ruta: str) -> str:
    return ruta.strip().rstrip("/")


def listar_assets_en_carpeta(parent: str) -> list[str]:
    """Lista todos los IDs bajo una carpeta GEE (con paginación)."""
    parent = _normalizar_ruta(parent)
    ids: list[str] = []
    page_token = None

    while True:
        req: dict = {"parent": parent}
        if page_token:
            req["pageToken"] = page_token
        resp = ee.data.listAssets(req)
        for asset in resp.get("assets", []):
            asset_id = asset.get("id")
            if asset_id:
                ids.append(asset_id)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return sorted(ids)


def asset_existe(asset_id: str) -> bool:
    try:
        ee.data.getAsset(asset_id)
        return True
    except Exception:
        return False


def crear_carpeta_destino(folder_id: str, dry_run: bool) -> None:
    folder_id = _normalizar_ruta(folder_id)
    if asset_existe(folder_id):
        print(f"Carpeta destino ya existe: {folder_id}")
        return
    if dry_run:
        print(f"[dry-run] Crearía carpeta: {folder_id}")
        return
    ee.data.createAsset({"type": "Folder", "id": folder_id})
    print(f"Carpeta creada: {folder_id}")


def copiar_con_reintentos(src: str, dst: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] {src}  ->  {dst}")
        return

    ultimo_error = None
    for intento in range(1, REINTENTOS + 1):
        try:
            ee.data.copyAsset(src, dst)
            return
        except Exception as exc:
            ultimo_error = exc
            if intento < REINTENTOS:
                pausa = PAUSA_BASE_SEG * intento
                print(f"  Reintento {intento}/{REINTENTOS} en {pausa:.1f}s ({exc})")
                time.sleep(pausa)
    raise RuntimeError(f"No se pudo copiar {src}: {ultimo_error}")


def migrar(
    origen: str,
    destino: str,
    *,
    dry_run: bool = False,
    skip_existing: bool = False,
    limit: int | None = None,
    crear_carpeta: bool = True,
) -> dict:
    origen = _normalizar_ruta(origen)
    destino = _normalizar_ruta(destino)

    if crear_carpeta:
        crear_carpeta_destino(destino, dry_run)

    origen_ids = listar_assets_en_carpeta(origen)
    if limit is not None:
        origen_ids = origen_ids[:limit]

    resumen = {
        "origen": origen,
        "destino": destino,
        "total_origen": len(origen_ids),
        "copiados": [],
        "omitidos": [],
        "errores": [],
    }

    print(f"Origen:  {origen} ({len(origen_ids)} assets)")
    print(f"Destino: {destino}")
    if dry_run:
        print("Modo: DRY-RUN (no se escribe en GEE)\n")

    for i, src in enumerate(origen_ids, start=1):
        nombre = src.rsplit("/", 1)[-1]
        dst = f"{destino}/{nombre}"
        prefijo = f"[{i}/{len(origen_ids)}]"

        if skip_existing and asset_existe(dst):
            print(f"{prefijo} Omitido (ya existe): {nombre}")
            resumen["omitidos"].append(dst)
            continue

        try:
            copiar_con_reintentos(src, dst, dry_run)
            print(f"{prefijo} OK: {nombre}")
            resumen["copiados"].append(dst)
            if not dry_run:
                time.sleep(PAUSA_ENTRE_COPIAS_SEG)
        except Exception as exc:
            print(f"{prefijo} ERROR: {nombre} — {exc}")
            resumen["errores"].append((src, str(exc)))

    return resumen


def _imprimir_resumen(resumen: dict) -> None:
    print("\n--- Resumen ---")
    print(f"Total en origen:  {resumen['total_origen']}")
    print(f"Copiados:         {len(resumen['copiados'])}")
    print(f"Omitidos:         {len(resumen['omitidos'])}")
    print(f"Errores:          {len(resumen['errores'])}")
    if resumen["errores"]:
        print("\nDetalle de errores:")
        for src, msg in resumen["errores"]:
            print(f"  - {src.split('/')[-1]}: {msg}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copia FeatureCollections de estadísticas entre carpetas GEE."
    )
    parser.add_argument(
        "--origen",
        default=ORIGEN_DEFAULT,
        help=f"Carpeta origen (default: {ORIGEN_DEFAULT})",
    )
    parser.add_argument(
        "--destino",
        default=DESTINO_DEFAULT,
        help=f"Carpeta destino (default: ASSET_PARENT = {DESTINO_DEFAULT})",
    )
    parser.add_argument(
        "--project",
        default="ee-my-andesnorte",
        help="Proyecto GCP para ee.Initialize (default: ee-my-andesnorte)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista lo que se copiaría sin llamar a copyAsset",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="No sobrescribe assets que ya existen en destino",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Copiar solo los primeros N assets (útil para prueba)",
    )
    parser.add_argument(
        "--no-crear-carpeta",
        action="store_true",
        help="No intenta crear la carpeta destino",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        ee.Initialize(project=args.project)
    except Exception as exc:
        print(f"Error al inicializar Earth Engine: {exc}", file=sys.stderr)
        print("Ejecuta: earthengine authenticate", file=sys.stderr)
        return 1

    resumen = migrar(
        args.origen,
        args.destino,
        dry_run=args.dry_run,
        skip_existing=args.skip_existing,
        limit=args.limit,
        crear_carpeta=not args.no_crear_carpeta,
    )
    _imprimir_resumen(resumen)

    if resumen["errores"]:
        return 2
    if resumen["total_origen"] == 0:
        print("\nNo se encontraron assets en origen.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
