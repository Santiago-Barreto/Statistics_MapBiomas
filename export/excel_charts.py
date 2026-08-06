"""
Exportación Excel con gráficas de evolución de coberturas (openpyxl).

Una hoja por versión + gráfico general e individuales con colores MapBiomas.
Escritura en un solo paso (sin roundtrip pandas→load_workbook) para evitar
corrupción de drawings que Excel repara al abrir.
"""

from __future__ import annotations

import io
import re
from typing import Mapping

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.utils.dataframe import dataframe_to_rows

from config import LEYENDA_MAPBIOMAS

COLUMNAS_EXCLUIR = {"system:index", "descripcion", "version", ".geo", "geo"}


def _colores_hex() -> dict[int, str]:
    return {
        int(cid): info["color"].lstrip("#").upper()
        for cid, info in LEYENDA_MAPBIOMAS.items()
    }


def _id_desde_header(header) -> int | None:
    if header is None:
        return None
    s = str(header).strip()
    m = re.match(r"^ID0*(\d+)$", s, re.IGNORECASE)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    return None


def _normalizar_cols_id(df: pd.DataFrame) -> pd.DataFrame:
    ren = {}
    for c in df.columns:
        if c in ("year", "version"):
            continue
        id_val = _id_desde_header(c)
        if id_val is not None:
            ren[c] = f"ID{id_val:02d}" if id_val < 100 else f"ID{id_val}"
    out = df.rename(columns=ren)
    return out.loc[:, ~out.columns.duplicated()]


def _nombre_proceso_hoja(asset_o_label: str) -> str:
    """
    Deriva el nombre de hoja tipo GAPFILL_V2 / CLASIFICACION_ORIGINAL_V1
    a partir del asset (R30450_V2-gapfill → GAPFILL_V2).
    """
    label = str(asset_o_label).rsplit("/", 1)[-1].replace("-", "_")
    m = re.search(r"_V(\d+)[_-]?(.*)$", label, re.IGNORECASE)
    if not m:
        return _sheet_name(label, set())

    version = m.group(1)
    sufijo = (m.group(2) or "").lower().strip("_")

    # Mapeo alineado a region_*_complete.xlsx
    if "join" in sufijo:
        nombre = "JOIN"
    elif "gapfill" in sufijo:
        nombre = "GAPFILL"
    elif "frecuencia" in sufijo:
        nombre = "FRECUENCIA"
    elif "temporal" in sufijo:
        nombre = "TEMPORAL"
    elif "espacial" in sufijo:
        nombre = "ESPACIAL"
    elif "mapageneral" in sufijo or "mapa_general" in sufijo:
        nombre = "MAPAGENERAL"
    elif "clasificacion" in sufijo or sufijo in ("", "v1"):
        nombre = "CLASIFICACION_ORIGINAL"
    elif sufijo:
        nombre = re.sub(r"[^A-Za-z0-9]+", "_", sufijo).strip("_").upper()
    else:
        nombre = "BASE"

    return f"{nombre}_V{version}"


def _sheet_name(nombre: str, usados: set[str]) -> str:
    limpio = re.sub(r"[\\/*?:\[\]]", "_", str(nombre))[:31] or "Hoja"
    base = limpio
    i = 1
    while limpio in usados:
        suf = f"_{i}"
        limpio = base[: 31 - len(suf)] + suf
        i += 1
    usados.add(limpio)
    return limpio


def _df_limpio(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    drop = [c for c in out.columns if c in COLUMNAS_EXCLUIR or c == "version"]
    out = out.drop(columns=drop, errors="ignore")
    out = _normalizar_cols_id(out)
    if "year" not in out.columns:
        raise ValueError("El DataFrame no tiene columna year")
    id_cols = sorted(
        [c for c in out.columns if _id_desde_header(c) is not None],
        key=lambda c: _id_desde_header(c) or 0,
    )
    out = out[["year"] + id_cols].sort_values("year")
    # Excel/openpyxl: NaN en series de gráfico corrompe drawings.
    out = out.fillna(0)
    out["year"] = out["year"].astype(int)
    for c in id_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
    return out


def _aplicar_color_serie(serie, color_hex: str) -> None:
    serie.graphicalProperties.line.solidFill = color_hex
    serie.graphicalProperties.line.width = 25000


def _agregar_graficos_hoja(ws, n_rows: int, n_cols: int, colores: dict[int, str]) -> None:
    """n_cols incluye year en la columna 1; IDs en 2..n_cols."""
    if n_rows < 2 or n_cols < 2:
        return

    headers = [ws.cell(row=1, column=c).value for c in range(1, n_cols + 1)]
    col_year = 1
    columnas_id = [i + 1 for i, h in enumerate(headers) if i > 0 and _id_desde_header(h) is not None]
    if not columnas_id:
        return

    cats = Reference(ws, min_col=col_year, min_row=2, max_row=n_rows)

    # --- Gráfico general (bloque contiguo de series) ---
    chart_all = LineChart()
    chart_all.title = "Evolución de Coberturas"
    chart_all.style = 10
    chart_all.height = 10
    chart_all.width = 20
    chart_all.y_axis.title = None
    chart_all.x_axis.title = None
    if chart_all.legend is not None:
        chart_all.legend.position = "b"

    data_all = Reference(
        ws,
        min_col=min(columnas_id),
        max_col=max(columnas_id),
        min_row=1,
        max_row=n_rows,
    )
    chart_all.add_data(data_all, titles_from_data=True)
    chart_all.set_categories(cats)

    for i, col_idx in enumerate(columnas_id):
        header = ws.cell(row=1, column=col_idx).value
        id_val = _id_desde_header(header) or 0
        if i < len(chart_all.series):
            _aplicar_color_serie(chart_all.series[i], colores.get(id_val, "000000"))

    ws.add_chart(chart_all, "H2")

    # --- Individuales ---
    start_row = 22
    for idx, col_idx in enumerate(columnas_id):
        header = ws.cell(row=1, column=col_idx).value
        id_val = _id_desde_header(header) or 0

        c = LineChart()
        c.title = str(header)
        c.style = 10
        c.height = 8
        c.width = 12
        c.legend = None

        d = Reference(ws, min_col=col_idx, min_row=1, max_row=n_rows)
        c.add_data(d, titles_from_data=True)
        c.set_categories(cats)
        if c.series:
            _aplicar_color_serie(c.series[0], colores.get(id_val, "000000"))

        col_pos = "H" if idx % 2 == 0 else "R"
        row_pos = start_row + (idx // 2) * 16
        ws.add_chart(c, f"{col_pos}{row_pos}")


def generar_excel_con_graficas_desde_data_dict(
    data_dict: Mapping[str, pd.DataFrame],
) -> bytes:
    """Genera un .xlsx en memoria: una hoja por entrada + gráficas."""
    if not data_dict:
        raise ValueError("No hay datos para exportar")

    colores = _colores_hex()
    wb = Workbook()
    # Quitar hoja por defecto vacía tras crear la primera real
    default = wb.active
    usados: set[str] = set()
    first = True

    for nombre, df in data_dict.items():
        # Preferir patrón NOMBRE_VX desde el asset/label (p. ej. GAPFILL_V2).
        hoja_raw = _nombre_proceso_hoja(nombre)
        hoja = _sheet_name(hoja_raw, usados)
        df_clean = _df_limpio(df)
        if first:
            ws = default
            ws.title = hoja
            first = False
        else:
            ws = wb.create_sheet(hoja)

        for row in dataframe_to_rows(df_clean, index=False, header=True):
            ws.append(row)

        n_rows = ws.max_row
        n_cols = ws.max_column
        _agregar_graficos_hoja(ws, n_rows, n_cols, colores)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def generar_excel_con_graficas_desde_region_xlsx(ruta_o_bytes) -> bytes:
    """Limpia REGIÓN_*.xlsx y añade gráficas (utilidad / tests)."""
    xls = pd.ExcelFile(ruta_o_bytes)
    data = {}
    for hoja in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=hoja)
        df = df.drop(columns=[c for c in COLUMNAS_EXCLUIR if c in df.columns])
        data[hoja] = df
    return generar_excel_con_graficas_desde_data_dict(data)
