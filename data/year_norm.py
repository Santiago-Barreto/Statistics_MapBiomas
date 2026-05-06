"""
Normalización de año para datos heterogéneos (SQLite / GEE).
Sin dependencias de Streamlit.
"""


def normalize_year(value):
    """
    Convierte un valor de año potencialmente str/float a int seguro.

    Retorna ``None`` si no es convertible.
    """
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
