from __future__ import annotations

from urllib.parse import quote
from utils.ticker_lookup import search_ticker_candidates
from utils.portfolio_tradingview import build_tradingview_symbol


def _clean(value: str) -> str:
    return str(value or "").strip().upper()


def _candidate_for_yf_symbol(yf_symbol: str) -> dict | None:
    clean_yf = _clean(yf_symbol)
    if not clean_yf:
        return None
    candidates = search_ticker_candidates(clean_yf)
    for candidate in candidates:
        if _clean(candidate.get("yf_symbol")) == clean_yf:
            return candidate
    return candidates[0] if candidates else None


def resolve_target_symbol(
    yf_symbol: str,
    *,
    ticker: str = "",
    name: str = "",
    market: str = "",
    currency: str = "",
    tv_symbol: str = "",
    source: str = "",
) -> dict:
    """Build a complete Target Analisti selection from a yfinance/watchlist symbol.

    Watchlist rows usually only know the yfinance symbol, while Target Analisti
    needs a correct TradingView symbol for the forecast page plus market/currency
    metadata. This resolver centralizes that conversion.
    """
    clean_yf = _clean(yf_symbol)
    clean_ticker = _clean(ticker) or clean_yf.replace(".MI", "")
    clean_market = _clean(market)
    clean_currency = _clean(currency)
    clean_tv = _clean(tv_symbol)
    clean_name = str(name or "").strip()

    candidate = _candidate_for_yf_symbol(clean_yf)
    if candidate:
        clean_ticker = _clean(candidate.get("ticker")) or clean_ticker
        clean_market = _clean(candidate.get("market")) or clean_market
        clean_currency = _clean(candidate.get("currency")) or clean_currency
        clean_tv = _clean(candidate.get("tv_symbol")) or clean_tv
        clean_name = str(candidate.get("name") or clean_name or clean_yf).strip()

    if not clean_market:
        clean_market = "MIL" if clean_yf.endswith(".MI") else "NASDAQ"

    if not clean_currency:
        clean_currency = "EUR" if clean_market == "MIL" else "USD"

    if not clean_tv:
        tv_ticker = clean_ticker
        if clean_market == "MIL" and tv_ticker.endswith(".MI"):
            tv_ticker = tv_ticker[:-3]
        clean_tv = build_tradingview_symbol(clean_market, tv_ticker, "", clean_currency)

    if not clean_name:
        clean_name = clean_yf

    return {
        "yf_symbol": clean_yf,
        "ticker": clean_ticker,
        "tv_symbol": clean_tv,
        "name": clean_name,
        "market": clean_market,
        "currency": clean_currency,
        "source": source,
    }


def tradingview_forecast_url(tv_symbol: str, yf_symbol: str = "", market: str = "", ticker: str = "") -> str:
    """Return a robust TradingView Forecast URL.

    Examples:
    NASDAQ:AAPL -> /symbols/NASDAQ-AAPL/forecast/
    NYSE:KO -> /symbols/NYSE-KO/forecast/
    MIL:1AMZN -> /symbols/MIL-1AMZN/forecast/
    """
    clean_tv = _clean(tv_symbol)
    if not clean_tv:
        resolved = resolve_target_symbol(yf_symbol, market=market, ticker=ticker)
        clean_tv = _clean(resolved.get("tv_symbol"))
    if clean_tv:
        return f"https://www.tradingview.com/symbols/{clean_tv.replace(':', '-')}/forecast/"
    return "https://www.tradingview.com/"


def tradingview_chart_url(tv_symbol: str = "", yf_symbol: str = "", market: str = "", ticker: str = "") -> str:
    """Return a robust TradingView chart URL using the resolved exchange symbol."""
    clean_tv = _clean(tv_symbol)
    if not clean_tv:
        resolved = resolve_target_symbol(yf_symbol, market=market, ticker=ticker)
        clean_tv = _clean(resolved.get("tv_symbol"))
    if clean_tv:
        encoded = quote(clean_tv, safe=":")
        return f"https://www.tradingview.com/chart/?symbol={encoded}"
    return "https://www.tradingview.com/chart/"
