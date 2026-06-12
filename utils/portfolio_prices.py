from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from utils.portfolio_storage import load_portfolio, save_portfolio


MARKET_SUFFIX_FOR_YFINANCE = {
    "MIL": ".MI",
    "BIT": ".MI",
    "MTA": ".MI",
    "XETRA": ".DE",
    "ETR": ".DE",
    "PAR": ".PA",
    "EPA": ".PA",
    "AMS": ".AS",
    "LSE": ".L",
    "SWX": ".SW",
    "SIX": ".SW",
}


def build_yfinance_symbol(ticker: str, mercato: str) -> str:
    clean_ticker = str(ticker or "").strip().upper()
    clean_market = str(mercato or "").strip().upper()

    if not clean_ticker:
        return ""

    suffix = MARKET_SUFFIX_FOR_YFINANCE.get(clean_market, "")
    if suffix and not clean_ticker.endswith(suffix):
        return f"{clean_ticker}{suffix}"

    return clean_ticker


@st.cache_data(ttl=120, show_spinner=False)
def fetch_last_quote(yf_symbol: str) -> dict:
    """Fetch last and previous close using yfinance, with safe fallbacks."""
    if not yf_symbol:
        return {"ok": False, "last": None, "previous": None, "error": "Simbolo vuoto"}

    try:
        import yfinance as yf
    except Exception as exc:
        return {
            "ok": False,
            "last": None,
            "previous": None,
            "error": f"yfinance non disponibile: {exc}",
        }

    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="5d", interval="1d", auto_adjust=False)

        if hist is None or hist.empty or "Close" not in hist.columns:
            return {"ok": False, "last": None, "previous": None, "error": "Storico vuoto"}

        close_values = hist["Close"].dropna()
        if close_values.empty:
            return {"ok": False, "last": None, "previous": None, "error": "Close vuoto"}

        last = float(close_values.iloc[-1])
        previous = float(close_values.iloc[-2]) if len(close_values) >= 2 else last

        return {"ok": True, "last": last, "previous": previous, "error": ""}
    except Exception as exc:
        return {"ok": False, "last": None, "previous": None, "error": str(exc)}


def refresh_portfolio_quotes(csv_path: Path) -> dict:
    """Refresh market and previous prices in CSV. Existing values are kept on errors."""
    df = load_portfolio(csv_path)

    updated = 0
    failed = []

    for idx, row in df.iterrows():
        yf_symbol = build_yfinance_symbol(row["ticker"], row["mercato"])
        result = fetch_last_quote(yf_symbol)

        if result.get("ok"):
            df.at[idx, "prezzo_mercato"] = result["last"]
            df.at[idx, "prezzo_precedente"] = result["previous"]
            updated += 1
        else:
            failed.append(f"{row['mercato']}:{row['ticker']} ({result.get('error', 'errore')})")

    save_portfolio(df, csv_path)

    return {
        "updated": updated,
        "failed": failed,
        "total": int(len(df)),
    }
