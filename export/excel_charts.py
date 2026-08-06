"""
Exportación Excel con gráficas (flujo Colab + mejoras visuales de tabla/leyenda).

Nombre de descarga esperado: region_{id}_complete.xlsx
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Mapping

import pandas as pd
from openpyxl import load_workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.marker import Marker
from openpyxl.chart.series import SeriesLabel
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from config import LEYENDA_MAPBIOMAS

COLUMNAS_EXCLUIR = ["system:index", "descripcion", "version", ".geo", "geo"]

# Colores MapBiomas (script original)
COLORES_ID = {
    1: "1F8D49",
    3: "1F8D49",
    5: "04381D",
    6: "026975",
    49: "02D659",
    10: "D6BC74",
    11: "519799",
    12: "D6BC74",
    32: "FC8114",
    29: "FFAA5F",
    50: "AD5100",
    14: "FFEFC3",
    9: "7A5900",
    35: "9065D0",
    74: "BE83F7",
    21: "FFEFC3",
    22: "D4271E",
    23: "FFA07A",
    24: "D4271E",
    30: "9C0027",
    68: "E97A7A",
    25: "DB4D4F",
    75: "C12100",
    26: "2532E4",
    33: "2532E4",
    31: "091077",
    34: "93DFE6",
    27: "000000",
}

_HEADER_FILL = PatternFill("solid", fgColor="1F8D49")
_HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
_CELL_FONT = Font(name="Calibri", size=10, color="333333")
_YEAR_FONT = Font(name="Calibri", size=10, bold=True, color="1F8D49")
_ALT_FILL = PatternFill("solid", fgColor="EAF5EE")
_THIN = Side(style="thin", color="C5D9CC")
_HEADER_BORDER = Border(bottom=Side(style="medium", color="0E5C2F"))
_CELL_BORDER = Border(bottom=_THIN)
_LEYENDA_TITLE_FONT = Font(name="Calibri", size=11, bold=True, color="1F8D49")
_LEYENDA_FONT = Font(name="Calibri", size=10, color="333333")


def _label_cobertura(id_val: int) -> str:
    return LEYENDA_MAPBIOMAS.get(id_val, {}).get("label", f"ID{id_val}")


def _id_desde_header(header) -> int | None:
    if header is None:
        return None
    s = str(header).strip()
    m = re.match(r"^ID0*(\d+)", s, re.IGNORECASE)
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
    """Deriva nombre de hoja tipo GAPFILL_V2 / CLASIFICACION_ORIGINAL_V1."""
    label = str(asset_o_label).rsplit("/", 1)[-1].replace("-", "_")

    m_ready = re.match(r"^([A-Za-zÁÉÍÓÚÑ_]+)_V(\d+)$", label, re.IGNORECASE)
    if m_ready:
        return f"{m_ready.group(1).upper()}_V{m_ready.group(2)}"

    m = re.search(r"_V(\d+)[_-]?(.*)$", label, re.IGNORECASE)
    if not m:
        return _sheet_name(label, set())

    version = m.group(1)
    sufijo = (m.group(2) or "").lower().strip("_")

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


def _df_para_hoja(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.drop(columns=[c for c in COLUMNAS_EXCLUIR if c in out.columns], errors="ignore")
    out = _normalizar_cols_id(out)
    if "year" not in out.columns:
        raise ValueError("El DataFrame no tiene columna year")
    id_cols = sorted(
        [c for c in out.columns if _id_desde_header(c) is not None],
        key=lambda c: _id_desde_header(c) or 0,
    )
    out = out[["year"] + id_cols].sort_values("year")
    out = out.fillna(0)
    out["year"] = out["year"].astype(int)
    for c in id_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
    return out


def _estilizar_tabla(ws) -> None:
    """Encabezado MapBiomas, filas alternas, números legibles, sin rejilla densa."""
    n_rows, n_cols = ws.max_row, ws.max_column
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 22

    for col in range(1, n_cols + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _HEADER_BORDER

    for row in range(2, n_rows + 1):
        for col in range(1, n_cols + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = _YEAR_FONT if col == 1 else _CELL_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = _CELL_BORDER
            if row % 2 == 0:
                cell.fill = _ALT_FILL
            cell.number_format = "0" if col == 1 else "#,##0.0"

    ws.column_dimensions["A"].width = 8
    for col in range(2, n_cols + 1):
        letter = get_column_letter(col)
        header = str(ws.cell(row=1, column=col).value or "")
        ws.column_dimensions[letter].width = max(10, min(14, len(header) + 3))


def _agregar_tabla_leyenda(ws, columnas_id: list[int]) -> None:
    """Bloque Leyenda bajo la tabla: color + ID + nombre (legible fuera del gráfico)."""
    start = ws.max_row + 2
    ws.cell(row=start, column=1, value="Leyenda").font = _LEYENDA_TITLE_FONT

    ws.cell(row=start + 1, column=1, value="Color").font = _HEADER_FONT
    ws.cell(row=start + 1, column=2, value="ID").font = _HEADER_FONT
    ws.cell(row=start + 1, column=3, value="Cobertura").font = _HEADER_FONT
    for col in range(1, 4):
        c = ws.cell(row=start + 1, column=col)
        c.fill = _HEADER_FILL
        c.alignment = Alignment(horizontal="center")

    for i, col_idx in enumerate(columnas_id):
        header = ws.cell(row=1, column=col_idx).value
        id_val = _id_desde_header(header) or 0
        color = COLORES_ID.get(id_val, "999999")
        r = start + 2 + i
        swatch = ws.cell(row=r, column=1, value="")
        swatch.fill = PatternFill("solid", fgColor=color)
        ws.cell(row=r, column=2, value=id_val).font = _LEYENDA_FONT
        ws.cell(row=r, column=2).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=3, value=_label_cobertura(id_val)).font = _LEYENDA_FONT
        ws.column_dimensions["C"].width = max(ws.column_dimensions["C"].width or 10, 28)


def _limpiar_formato_grafico(chart) -> None:
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.y_axis.majorGridlines = None
    chart.x_axis.majorGridlines = None
    chart.x_axis.tickLblSkip = 0


def _aplicar_serie(serie, color_hex: str, titulo: str | None = None) -> None:
    serie.graphicalProperties.line.solidFill = color_hex
    serie.graphicalProperties.line.width = 22000
    mk = Marker(symbol=None)
    mk.spPr = None
    serie.marker = mk
    serie.smooth = False
    if titulo:
        serie.title = SeriesLabel(v=titulo)


def _agregar_graficos_hoja(ws) -> None:
    headers = [cell.value for cell in ws[1]]
    if "year" not in headers:
        return

    col_year = headers.index("year") + 1
    columnas_id = [
        i + 1 for i, col in enumerate(headers) if str(col).startswith("ID")
    ]
    if not columnas_id:
        return

    # Estilo de tabla + leyenda legible (antes de charts: max_row de datos)
    n_data_rows = ws.max_row
    _estilizar_tabla(ws)
    _agregar_tabla_leyenda(ws, columnas_id)

    cats = Reference(ws, min_col=col_year, min_row=2, max_row=n_data_rows)

    # 1) Gráfico general — leyenda abajo, series con nombre de cobertura
    chart_all = LineChart()
    chart_all.title = "Evolución de Coberturas"
    chart_all.height, chart_all.width = 10, 38
    if chart_all.legend is not None:
        chart_all.legend.position = "b"

    for col_idx in columnas_id:
        data = Reference(ws, min_col=col_idx, min_row=1, max_row=n_data_rows)
        chart_all.add_data(data, titles_from_data=True)

    chart_all.set_categories(cats)
    _limpiar_formato_grafico(chart_all)

    for i, col_idx in enumerate(columnas_id):
        header = ws.cell(row=1, column=col_idx).value
        id_val = _id_desde_header(header) or 0
        color = COLORES_ID.get(id_val, "000000")
        if i < len(chart_all.series):
            _aplicar_serie(
                chart_all.series[i],
                color,
                titulo=_label_cobertura(id_val),
            )

    ws.add_chart(chart_all, "H2")

    # 2) Individuales — título = nombre de cobertura
    start_row = 22
    for idx, col_idx in enumerate(columnas_id):
        header = ws.cell(row=1, column=col_idx).value
        id_val = _id_desde_header(header) or 0
        color = COLORES_ID.get(id_val, "000000")
        titulo = _label_cobertura(id_val)

        c = LineChart()
        c.title = titulo
        c.height, c.width = 6, 18
        c.legend = None

        d = Reference(ws, min_col=col_idx, min_row=1, max_row=n_data_rows)
        c.add_data(d, titles_from_data=True)
        c.set_categories(cats)
        _limpiar_formato_grafico(c)

        if c.series:
            _aplicar_serie(c.series[0], color, titulo=titulo)

        col_pos = "H" if idx % 2 == 0 else "Z"
        row_pos = start_row + (idx // 2) * 15
        ws.add_chart(c, f"{col_pos}{row_pos}")


def generar_excel_con_graficas_desde_data_dict(
    data_dict: Mapping[str, pd.DataFrame],
) -> bytes:
    """Genera un .xlsx en memoria: una hoja por entrada + gráficas."""
    if not data_dict:
        raise ValueError("No hay datos para exportar")

    usados: set[str] = set()
    limpios: dict[str, pd.DataFrame] = {}
    for nombre, df in data_dict.items():
        hoja = _sheet_name(_nombre_proceso_hoja(nombre), usados)
        limpios[hoja] = _df_para_hoja(df)

    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "complete.xlsx"
        with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
            for hoja, df in limpios.items():
                df.to_excel(writer, sheet_name=hoja, index=False)

        wb = load_workbook(ruta)
        for hoja in wb.sheetnames:
            _agregar_graficos_hoja(wb[hoja])
        wb.save(ruta)
        return ruta.read_bytes()


def generar_excel_con_graficas_desde_region_xlsx(ruta_o_bytes) -> bytes:
    """Limpia REGIÓN_*.xlsx y añade gráficas (utilidad / tests)."""
    xls = pd.ExcelFile(ruta_o_bytes)
    data = {}
    for hoja in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=hoja)
        df = df.drop(columns=[c for c in COLUMNAS_EXCLUIR if c in df.columns])
        data[hoja] = df
    return generar_excel_con_graficas_desde_data_dict(data)
