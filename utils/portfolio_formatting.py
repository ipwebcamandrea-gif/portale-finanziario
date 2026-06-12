def fmt_num(value: float, decimals: int = 2) -> str:
    """Format a number using Italian thousands and decimal separators."""
    try:
        return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "-"


def fmt_qty(value: float) -> str:
    """Format a quantity with compact decimals only when needed."""
    try:
        numeric_value = float(value)
        if numeric_value.is_integer():
            return f"{int(numeric_value):,}".replace(",", ".")
        return fmt_num(numeric_value, 4)
    except Exception:
        return "-"


def fmt_eur(value: float) -> str:
    return fmt_num(value, 2)


def fmt_pct(value: float) -> str:
    return f"{fmt_num(value, 2)}%"


def value_class(value: float) -> str:
    try:
        numeric_value = float(value)
    except Exception:
        return "portfolio-neutral"

    if numeric_value > 0:
        return "portfolio-positive"

    if numeric_value < 0:
        return "portfolio-negative"

    return "portfolio-neutral"
