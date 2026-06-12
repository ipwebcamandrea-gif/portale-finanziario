from __future__ import annotations

import math

import pandas as pd

from utils.portfolio_fx import get_fx_rates_to_eur


def _is_valid_rate(value) -> bool:
    try:
        numeric = float(value)
        return math.isfinite(numeric) and numeric > 0
    except Exception:
        return False


def enrich_portfolio_df(df: pd.DataFrame, fx_rates: dict | None = None) -> pd.DataFrame:
    """Add calculated EUR values and performance metrics to the portfolio dataframe.

    FX rates are retrieved centrally from `utils.portfolio_fx` through yfinance.
    Non-EUR currencies are not converted with a fake fallback rate.
    """
    enriched = df.copy()

    if enriched.empty:
        for col in [
            "fx_eur",
            "fx_missing",
            "valore_carico_eur",
            "valore_mercato_eur",
            "var_quotidiana_eur",
            "var_quotidiana_pct",
            "var_da_carico_eur",
            "var_da_carico_pct",
        ]:
            enriched[col] = []
        return enriched

    enriched["valuta"] = enriched["valuta"].fillna("").astype(str).str.upper()

    if fx_rates is None:
        fx_rates, fx_errors = get_fx_rates_to_eur(enriched["valuta"].unique())
    else:
        fx_errors = {}

    enriched["fx_eur"] = enriched["valuta"].map(fx_rates)
    enriched["fx_missing"] = ~enriched["fx_eur"].apply(_is_valid_rate)

    enriched["valore_carico_eur"] = (
        enriched["quantita"] * enriched["prezzo_medio"] * enriched["fx_eur"]
    )

    enriched["valore_mercato_eur"] = (
        enriched["quantita"] * enriched["prezzo_mercato"] * enriched["fx_eur"]
    )

    enriched["var_quotidiana_eur"] = (
        enriched["quantita"]
        * (enriched["prezzo_mercato"] - enriched["prezzo_precedente"])
        * enriched["fx_eur"]
    )

    enriched["var_quotidiana_pct"] = enriched.apply(
        lambda row: (
            (row["prezzo_mercato"] - row["prezzo_precedente"])
            / row["prezzo_precedente"]
            * 100
        )
        if row["prezzo_precedente"] != 0
        else 0,
        axis=1,
    )

    enriched["var_da_carico_eur"] = (
        enriched["quantita"]
        * (enriched["prezzo_mercato"] - enriched["prezzo_medio"])
        * enriched["fx_eur"]
    )

    enriched["var_da_carico_pct"] = enriched.apply(
        lambda row: (
            (row["prezzo_mercato"] - row["prezzo_medio"])
            / row["prezzo_medio"]
            * 100
        )
        if row["prezzo_medio"] != 0
        else 0,
        axis=1,
    )

    enriched.attrs["fx_errors"] = fx_errors

    return enriched


def portfolio_totals(df: pd.DataFrame) -> dict:
    """Calculate total portfolio summary values."""
    valore_carico = float(df["valore_carico_eur"].sum(skipna=True)) if not df.empty else 0.0
    valore_mercato = float(df["valore_mercato_eur"].sum(skipna=True)) if not df.empty else 0.0
    var_da_carico = valore_mercato - valore_carico

    var_da_carico_pct = (
        var_da_carico / valore_carico * 100 if valore_carico != 0 else 0.0
    )

    var_quotidiana = float(df["var_quotidiana_eur"].sum(skipna=True)) if not df.empty else 0.0

    return {
        "valore_carico": valore_carico,
        "valore_mercato": valore_mercato,
        "var_da_carico": var_da_carico,
        "var_da_carico_pct": var_da_carico_pct,
        "var_quotidiana": var_quotidiana,
    }
