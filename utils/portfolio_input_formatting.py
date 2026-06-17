from __future__ import annotations


QTY_INPUT_STEP = 1
QTY_INPUT_FORMAT = "%d"

PRICE_INPUT_STEP = 0.01
PRICE_INPUT_FORMAT = "%.2f"


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def normalize_quantity(value) -> int:
    """Normalize portfolio quantity inputs to whole units."""
    number = _safe_float(value)
    if number < 0:
        return 0
    return int(round(number))


def normalize_price(value) -> float:
    """Normalize portfolio price inputs to two decimals."""
    number = _safe_float(value)
    if number < 0:
        return 0.0
    return round(number, 2)
