"""UI: descarga de Excel con gráficas de coberturas."""

import streamlit as st

from export.excel_charts import (
    generar_excel_con_graficas_desde_data_dict,
    generar_excel_con_graficas_desde_region_xlsx,
)


def render_excel_export_panel(region_id, data_dict):
    """
    Panel para generar R{region}.xlsx con gráficas (versiones seleccionadas)
    o a partir de un REGIÓN_*.xlsx subido.
    """
    st.markdown("#### 📥 Excel con gráficas")
    st.caption(
        "Genera un archivo como tu flujo Colab: una hoja por versión, "
        "gráfico general + individuales con colores MapBiomas."
    )

    col_a, col_b = st.columns(2)

    with col_a:
        if data_dict:
            try:
                payload = generar_excel_con_graficas_desde_data_dict(data_dict)
                nombre = f"R{region_id}.xlsx"
                st.download_button(
                    label=f"Descargar {nombre} (selección actual)",
                    data=payload,
                    file_name=nombre,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"dl_excel_sel_{region_id}",
                )
            except Exception as exc:
                st.error(f"No se pudo generar el Excel: {exc}")
        else:
            st.info("Selecciona al menos una versión con datos.")

    with col_b:
        uploaded = st.file_uploader(
            "O sube REGIÓN_XXXXX.xlsx (varias hojas)",
            type=["xlsx"],
            key=f"up_region_xlsx_{region_id}",
        )
        if uploaded is not None:
            try:
                region_match = str(region_id)
                name = uploaded.name
                if "REGIÓN_" in name.upper() or "REGION_" in name.upper():
                    # REGIÓN_30450.xlsx -> R30450.xlsx
                    import re

                    m = re.search(r"(\d{4,})", name)
                    if m:
                        region_match = m.group(1)
                payload = generar_excel_con_graficas_desde_region_xlsx(uploaded)
                st.download_button(
                    label=f"Descargar R{region_match}.xlsx (desde archivo)",
                    data=payload,
                    file_name=f"R{region_match}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"dl_excel_up_{region_id}",
                )
            except Exception as exc:
                st.error(f"Error procesando el archivo: {exc}")
