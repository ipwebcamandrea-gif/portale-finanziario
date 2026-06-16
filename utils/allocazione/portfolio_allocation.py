from __future__ import annotations

import math

import pandas as pd


def _safe_float(value, default: float = 0.0) -> float:
    try:
        numeric = float(value)
        if math.isfinite(numeric):
            return numeric
    except Exception:
        pass
    return default


def _safe_text(value, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _display_symbol_from_row(row) -> str:
    """Return the best symbol to show in allocation rows.

    Prefer tv_symbol when present, e.g. MIL:1MSFT, otherwise fallback to
    mercato:ticker, e.g. NASDAQ:MSFT.
    """
    tv_symbol = _safe_text(row.get("tv_symbol", "")).upper()
    if tv_symbol:
        return tv_symbol

    market = _safe_text(row.get("mercato", "")).upper()
    ticker = _safe_text(row.get("ticker", "")).upper()

    if market and ticker:
        return f"{market}:{ticker}"
    return ticker or market or "-"


def _display_market_from_row(row) -> str:
    """Return market part from tv_symbol if available, otherwise mercato."""
    display_symbol = _display_symbol_from_row(row)
    if ":" in display_symbol:
        return display_symbol.split(":", 1)[0].strip().upper()
    return _safe_text(row.get("mercato", "N/D"), "N/D").upper()


def _weight_series(df: pd.DataFrame, value_col: str) -> pd.Series:
    values = pd.to_numeric(df[value_col], errors="coerce").fillna(0.0)
    total = float(values.sum())
    if total <= 0:
        return pd.Series([0.0] * len(df), index=df.index)
    return values / total * 100


def calculate_position_allocation(df: pd.DataFrame, value_col: str = "valore_mercato_eur") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "ticker",
                "titolo",
                "mercato",
                "valuta",
                "tv_symbol",
                "display_symbol",
                "display_market",
                "value_eur",
                "weight_pct",
            ]
        )

    allocation = df.copy()
    allocation["ticker"] = allocation["ticker"].apply(_safe_text)
    allocation["titolo"] = allocation["titolo"].apply(lambda value: _safe_text(value, "-").upper())
    allocation["mercato"] = allocation["mercato"].apply(_safe_text)
    allocation["valuta"] = allocation["valuta"].apply(_safe_text)

    if "tv_symbol" not in allocation.columns:
        allocation["tv_symbol"] = ""
    allocation["tv_symbol"] = allocation["tv_symbol"].apply(_safe_text)

    allocation["display_symbol"] = allocation.apply(_display_symbol_from_row, axis=1)
    allocation["display_market"] = allocation.apply(_display_market_from_row, axis=1)

    allocation["value_eur"] = pd.to_numeric(allocation[value_col], errors="coerce").fillna(0.0)
    allocation["weight_pct"] = _weight_series(allocation, "value_eur")

    return allocation.sort_values(by="value_eur", ascending=False, kind="mergesort").reset_index(drop=True)


def calculate_group_allocation(df: pd.DataFrame, group_col: str, value_col: str = "valore_mercato_eur") -> pd.DataFrame:
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=[group_col, "value_eur", "weight_pct"])

    source = df.copy()

    # Market allocation should use the market actually shown by tv_symbol when available.
    # Example: tv_symbol MIL:1MSFT means market MIL, even if the legacy mercato field is NASDAQ.
    if group_col == "mercato":
        if "tv_symbol" not in source.columns:
            source["tv_symbol"] = ""
        source[group_col] = source.apply(_display_market_from_row, axis=1)

    grouped = (
        source.assign(_value=pd.to_numeric(source[value_col], errors="coerce").fillna(0.0))
        .groupby(group_col, dropna=False)["_value"]
        .sum()
        .reset_index()
        .rename(columns={"_value": "value_eur"})
    )

    grouped[group_col] = grouped[group_col].apply(lambda value: _safe_text(value, "N/D").upper())
    total = float(grouped["value_eur"].sum())
    grouped["weight_pct"] = grouped["value_eur"] / total * 100 if total > 0 else 0.0

    return grouped.sort_values(by="value_eur", ascending=False, kind="mergesort").reset_index(drop=True)


def calculate_concentration_metrics(position_allocation: pd.DataFrame) -> dict:
    if position_allocation.empty:
        return {"total_value": 0.0, "positions_count": 0, "top_title": "-", "top_weight_pct": 0.0, "top3_weight_pct": 0.0}

    top_row = position_allocation.iloc[0]
    return {
        "total_value": float(position_allocation["value_eur"].sum()),
        "positions_count": int(len(position_allocation)),
        "top_title": str(top_row.get("titolo", "-")),
        "top_weight_pct": _safe_float(top_row.get("weight_pct")),
        "top3_weight_pct": float(position_allocation.head(3)["weight_pct"].sum()),
    }


def concentration_label(weight_pct: float) -> str:
    weight = _safe_float(weight_pct)
    if weight >= 35:
        return "Peso molto alto"
    if weight >= 20:
        return "Peso alto"
    if weight >= 10:
        return "Peso medio"
    return "Peso contenuto"


def concentration_class(weight_pct: float) -> str:
    weight = _safe_float(weight_pct)
    if weight >= 35:
        return "allocation-concentration-very-high"
    if weight >= 20:
        return "allocation-concentration-high"
    if weight >= 10:
        return "allocation-concentration-medium"
    return "allocation-concentration-low"


def build_allocation_insights(position_allocation: pd.DataFrame, currency_allocation: pd.DataFrame, market_allocation: pd.DataFrame, metrics: dict) -> list[str]:
    count = int(metrics.get("positions_count", 0) or 0)
    if count == 0:
        return ["Il portafoglio non contiene posizioni da analizzare."]

    insights = [
        f"Tutti i {count} titoli sono visibili nel grafico e nella lista pesi.",
        f"La posizione più grande è {metrics.get('top_title', '-')} con circa {metrics.get('top_weight_pct', 0.0):.2f}% del portafoglio.",
        f"Le prime 3 posizioni rappresentano circa {metrics.get('top3_weight_pct', 0.0):.2f}% del portafoglio.",
    ]

    if not currency_allocation.empty:
        row = currency_allocation.iloc[0]
        insights.append(f"La valuta più rappresentata è {row.iloc[0]} con circa {float(row['weight_pct']):.2f}% del valore totale.")

    if not market_allocation.empty:
        row = market_allocation.iloc[0]
        insights.append(f"Il mercato più rappresentato è {row.iloc[0]} con circa {float(row['weight_pct']):.2f}% del valore totale.")

    insights.append("Insight informativi: non costituiscono consulenza finanziaria.")
    return insights
