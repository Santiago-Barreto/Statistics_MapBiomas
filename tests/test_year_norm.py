"""Normalización centralizada de año (uso en BD y sincronización)."""

import pytest

from data.year_norm import normalize_year


@pytest.mark.parametrize(
    "raw,expected",
    [
        (2026, 2026),
        ("2026", 2026),
        (2026.5, 2026),
        ("2025.0", 2025),
        (None, None),
        ("", None),
        ("abc", None),
    ],
)
def test_normalize_year(raw, expected):
    assert normalize_year(raw) == expected
