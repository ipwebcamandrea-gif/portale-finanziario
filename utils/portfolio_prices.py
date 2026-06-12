from __future__ import annotations

from pathlib import Path

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


def build_yfinance_symbol(ticker: str, mercato: str, yf_symbol: str = "") -> str:
    """Return the yfinance symbol to use for quotes.

    `yf_symbol` wins when present. This is required for EUR listings such as
    `1MSFT.MI`, because using plain `MSFT` would fetch the USD Nasdaq quote.
    """
    explicit_symbol = str(yf_symbol or "").strip().upper()
    if explicit_symbol:
        return explicit_symbol

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

        # Prefer fast_info for the most recent price when available.
        last = None
        previous = None
        try:
            fast_info = ticker.fast_info
            last = fast_info.get("last_price") or fast_info.get("lastPrice")
            previous = fast_info.get("previous_close") or fast_info.get("previousClose")
            if last is not None:
                last = float(last)
            if previous is not None:
                previous = float(previous)
        except Exception:
            pass

        hist = ticker.history(period="5d", interval="1d", auto_adjust=False)
        if hist is not None and not hist.empty and "Close" in hist.columns:
            close_values = hist["Close"].dropna()
            if not close_values.empty:
                if last is None:
                    last = float(close_values.iloc[-1])
                if previous is None:
                    previous = float(close_values.iloc[-2]) if len(close_values) >= 2 else last

        if last is None:
            return {"ok": False, "last": None, "previous": None, "error": "Prezzo non disponibile"}

        if previous is None:
            previous = last

        return {"ok": True, "last": float(last), "previous": float(previous), "error": ""}
    except Exception as exc:
        return {"ok": False, "last": None, "previous": None, "error": str(exc)}


def refresh_portfolio_quotes(csv_path: Path) -> dict:
    """Refresh market and previous prices in CSV. Existing values are kept on errors."""
    df = load_portfolio(csv_path)

    updated = 0
    failed = []

    for idx, row in df.iterrows():
        yf_symbol = build_yfinance_symbol(
            row.get("ticker", ""),
            row.get("mercato", ""),
            row.get("yf_symbol", ""),
        )
        result = fetch_last_quote(yf_symbol)

        if result.get("ok"):
            df.at[idx, "prezzo_mercato"] = result["last"]
            df.at[idx, "prezzo_precedente"] = result["previous"]
            updated += 1
        else:
            failed.append(
                f"{row.get('mercato', '')}:{row.get('ticker', '')} / {yf_symbol} ({result.get('error', 'errore')})"
            )

    save_portfolio(df, csv_path)

    return {
        "updated": updated,
        "failed": failed,
        "total": int(len(df)),
    }
