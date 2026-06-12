import pandas as pd


DEFAULT_FX_RATES_EUR = {
    "EUR": 1.0,
    "USD": 0.92,
    "GBP": 1.18,
    "CHF": 1.05,
}


def enrich_portfolio_df(df: pd.DataFrame, fx_rates: dict | None = None) -> pd.DataFrame:
    """Add calculated EUR values and performance metrics to the portfolio dataframe."""
    if fx_rates is None:
        fx_rates = DEFAULT_FX_RATES_EUR

    enriched = df.copy()

    enriched["fx_eur"] = enriched["valuta"].map(fx_rates).fillna(1.0)

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

    return enriched


def portfolio_totals(df: pd.DataFrame) -> dict:
    """Calculate total portfolio summary values."""
    valore_carico = float(df["valore_carico_eur"].sum()) if not df.empty else 0.0
    valore_mercato = float(df["valore_mercato_eur"].sum()) if not df.empty else 0.0
    var_da_carico = valore_mercato - valore_carico

    var_da_carico_pct = (
        var_da_carico / valore_carico * 100 if valore_carico != 0 else 0.0
    )

    var_quotidiana = float(df["var_quotidiana_eur"].sum()) if not df.empty else 0.0

    return {
        "valore_carico": valore_carico,
        "valore_mercato": valore_mercato,
        "var_da_carico": var_da_carico,
        "var_da_carico_pct": var_da_carico_pct,
        "var_quotidiana": var_quotidiana,
    }
