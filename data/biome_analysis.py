"""Utilidades analíticas para aportes regionales en modo bioma."""

import pandas as pd


def construir_heatmap_cambios(df_cov):
    """
    Construye la matriz (región x periodo) con cambios interanuales en hectáreas.
    """
    if df_cov is None or df_cov.empty:
        return pd.DataFrame()

    pivot = (
        df_cov.pivot_table(
            index="region",
            columns="year",
            values="area_ha",
            aggfunc="sum",
            fill_value=0.0,
        )
        .sort_index(axis=1)
        .sort_index(axis=0)
    )
    if pivot.shape[1] < 2:
        return pd.DataFrame(index=pivot.index)

    cambios = pivot.diff(axis=1).iloc[:, 1:]
    cambios.columns = [f"{int(y - 1)}→{int(y)}" for y in cambios.columns]
    return cambios


def construir_tabla_linea_temporal(df_cov):
    """
    Retorna la línea temporal completa por región con ganancia/pérdida anual.
    """
    if df_cov is None or df_cov.empty:
        return pd.DataFrame()

    base = (
        df_cov.groupby(["region", "year"], as_index=False)["area_ha"]
        .sum()
        .sort_values(["region", "year"])
    )
    base["delta_ha"] = base.groupby("region")["area_ha"].diff()
    base["sentido"] = base["delta_ha"].apply(
        lambda x: "Base" if pd.isna(x) else ("Ganancia" if x >= 0 else "Pérdida")
    )
    return base.reset_index(drop=True)
