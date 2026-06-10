import re


# =========================
# SYMBOL HELPERS
# =========================

def slug_safe(value):
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(value)).strip("_") or "item"


def simbolo_tradingview(symbol):
    """
    Conversione pratica Yahoo Finance -> TradingView per link esterno.

    Esempi:
    - AAPL      -> NASDAQ:AAPL
    - MSFT      -> NASDAQ:MSFT
    - JPM       -> NYSE:JPM
    - SWDA.MI   -> MIL:SWDA

    Se il simbolo contiene gia il mercato TradingView, viene mantenuto.
    """
    symbol = str(symbol or "").strip().upper()

    if not symbol:
        return "NASDAQ:AAPL"

    if ":" in symbol:
        return symbol

    if symbol.endswith(".MI"):
        return "MIL:" + symbol.replace(".MI", "")

    nasdaq_symbols = {
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "NFLX", "ADBE",
        "AMD", "INTC", "CSCO", "AVGO", "QCOM", "TXN", "PEP", "COST", "AMAT", "MU",
        "PYPL", "SBUX", "ISRG", "BKNG", "LRCX", "PANW", "CRWD", "SHOP", "ARM", "SMCI"
    }

    nyse_symbols = {
        "JPM", "BAC", "V", "MA", "BRK.B", "BRK.A", "KO", "PG", "JNJ", "UNH", "HD",
        "DIS", "IBM", "ORCL", "CRM", "CVX", "XOM", "WMT", "MCD", "NKE", "CAT",
        "BA", "GS", "MS", "AXP", "GE", "T", "VZ", "PFE", "MRK", "LLY"
    }

    if symbol in nasdaq_symbols:
        return "NASDAQ:" + symbol

    if symbol in nyse_symbols:
        return "NYSE:" + symbol

    return "NASDAQ:" + symbol


def url_tradingview(symbol):
    tv_symbol = simbolo_tradingview(symbol)
    return "https://www.tradingview.com/chart/?symbol=" + tv_symbol
