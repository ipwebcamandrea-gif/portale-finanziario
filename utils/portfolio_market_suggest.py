from __future__ import annotations

from functools import lru_cache


DEFAULT_MARKET = "NASDAQ"
MARKET_OPTIONS = ["NASDAQ", "NYSE", "AMEX", "ARCA", "MIL"]

NASDAQ_TICKERS = {
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA",
    "NFLX", "ADBE", "AMD", "INTC", "CSCO", "AVGO", "QCOM", "TXN",
    "PEP", "COST", "AMAT", "MU", "PYPL", "SBUX", "ISRG", "BKNG",
    "LRCX", "PANW", "CRWD", "SHOP", "ARM", "SMCI", "SOFI", "MSTR",
    "PLTR", "ASML", "ADP", "INTU", "REGN", "VRTX", "ABNB", "MELI",
}

NYSE_TICKERS = {
    "JPM", "BAC", "V", "MA", "BRK.B", "BRK.A", "KO", "PG", "JNJ",
    "UNH", "HD", "DIS", "IBM", "ORCL", "CRM", "CVX", "XOM", "WMT",
    "MCD", "NKE", "CAT", "BA", "GS", "MS", "AXP", "GE", "T", "VZ",
    "PFE", "MRK", "LLY", "ABBV", "TMO", "LIN", "NOW", "UBER", "SQ",
}

YFINANCE_EXCHANGE_TO_MARKET = {
    "NMS": "NASDAQ",
    "NGM": "NASDAQ",
    "NCM": "NASDAQ",
    "NASDAQ": "NASDAQ",
    "NASDAQGS": "NASDAQ",
    "NASDAQGM": "NASDAQ",
    "NASDAQCM": "NASDAQ",
    "NYQ": "NYSE",
    "NYSE": "NYSE",
    "NYE": "NYSE",
    "ASE": "AMEX",
    "AMEX": "AMEX",
    "PCX": "ARCA",
    "ARCA": "ARCA",
    "MIL": "MIL",
    "MILAN": "MIL",
}


def clean_ticker(ticker: str) -> str:
    return str(ticker or "").strip().upper()


def _result(ticker: str, market: str, confidence: str, source: str, message: str) -> dict:
    return {
        "ticker": clean_ticker(ticker),
        "market": market,
        "confidence": confidence,
        "source": source,
        "message": message,
    }


@lru_cache(maxsize=256)
def _fetch_yfinance_exchange(ticker: str) -> tuple[str, str]:
    """Return yfinance exchange and display exchange, without raising."""
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).get_info() or {}
        exchange = str(info.get("exchange") or "").strip().upper()
        full_exchange = str(info.get("fullExchangeName") or "").strip()
        return exchange, full_exchange
    except Exception:
        return "", ""


def suggest_market_for_ticker(ticker: str) -> dict:
    """Suggest the most likely TradingView market for a portfolio ticker.

    The function first uses a small local map for common US tickers, then falls
    back to yfinance exchange metadata. The UI must still expose a selectbox so
    the user can override the suggestion manually.
    """
    symbol = clean_ticker(ticker)

    if not symbol:
        return _result(symbol, DEFAULT_MARKET, "low", "default", "Mercato default: NASDAQ")

    if ":" in symbol:
        market = symbol.split(":", 1)[0].strip().upper() or DEFAULT_MARKET
        if market not in MARKET_OPTIONS:
            market = DEFAULT_MARKET
        return _result(symbol, market, "high", "ticker_prefix", f"Mercato letto dal prefisso: {market}")

    if symbol.endswith(".MI") or symbol.startswith("1"):
        return _result(symbol, "MIL", "medium", "local_rule", "Mercato suggerito: MIL")

    if symbol in NASDAQ_TICKERS:
        return _result(symbol, "NASDAQ", "high", "local_map", "Mercato suggerito: NASDAQ")

    if symbol in NYSE_TICKERS:
        return _result(symbol, "NYSE", "high", "local_map", "Mercato suggerito: NYSE")

    exchange, full_exchange = _fetch_yfinance_exchange(symbol)
    market = YFINANCE_EXCHANGE_TO_MARKET.get(exchange)

    if market:
        detail = f" da yfinance ({exchange}"
        if full_exchange:
            detail += f" · {full_exchange}"
        detail += ")"
        return _result(symbol, market, "medium", "yfinance", f"Mercato suggerito: {market}{detail}")

    return _result(
        symbol,
        DEFAULT_MARKET,
        "low",
        "default",
        "Mercato non determinato: verifica la selectbox prima di aggiungere.",
    )
