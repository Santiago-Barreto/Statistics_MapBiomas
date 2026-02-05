import ee
import os
from config import ASSET_PARENT

def listar_versiones_disponibles(region_id):
    try:
        assets = ee.data.listAssets({"parent": ASSET_PARENT}).get("assets", [])
        versiones = []

        for a in assets:
            asset_id = os.path.basename(a["id"])
            if asset_id.startswith(region_id + "_"):
                versiones.append(asset_id.replace(f"{region_id}_", ""))

        return sorted(versiones)

    except Exception:
        return []


def leer_stats_procesadas(nombre_asset):
    ruta = f"{ASSET_PARENT}/{nombre_asset}"
    try:
        fc = ee.FeatureCollection(ruta)
        feats = fc.getInfo().get("features", [])
        return [f["properties"] for f in feats]
    except Exception:
        return []
