import re
from urllib.parse import quote


# =========================
# SYMBOL HELPERS
# =========================

def slug_safe(value):
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(value)).strip("_") or "item"


# =========================
# NORMALIZZAZIONE YFINANCE / TRADINGVIEW
# =========================

def clean_symbol(symbol):
    return str(symbol or "").strip().upper().replace(" ", "")


def strip_exchange_prefix(symbol):
    symbol = clean_symbol(symbol)
    if ":" in symbol:
        return symbol.split(":", 1)[1]
    return symbol


def normalize_yfinance_symbol(symbol):
    """
    Normalizza il simbolo per Yahoo Finance / yfinance.

    Caso importante:
    - BRK.B / NYSE:BRK.B -> BRK-B
    - BRK.A / NYSE:BRK.A -> BRK-A

    I suffissi tipo .MI vengono mantenuti.
    """
    symbol = clean_symbol(symbol)

    aliases = {
        "BRK.B": "BRK-B",
        "BRK-B": "BRK-B",
        "BRK/B": "BRK-B",
        "NYSE:BRK.B": "BRK-B",
        "NYSE:BRK-B": "BRK-B",
        "BRK.A": "BRK-A",
        "BRK-A": "BRK-A",
        "BRK/A": "BRK-A",
        "NYSE:BRK.A": "BRK-A",
        "NYSE:BRK-A": "BRK-A",
        "BF.B": "BF-B",
        "BF-B": "BF-B",
        "NYSE:BF.B": "BF-B",
        "NYSE:BF-B": "BF-B",
    }

    if symbol in aliases:
        return aliases[symbol]

    no_exchange = strip_exchange_prefix(symbol)

    if no_exchange in aliases:
        return aliases[no_exchange]

    # Class shares USA generiche: ABC.B -> ABC-B.
    # Non tocca suffissi exchange a due lettere tipo .MI / .PA / .DE.
    if re.match(r"^[A-Z]{1,6}\.[A-Z]$", no_exchange):
        return no_exchange.replace(".", "-")

    return no_exchange


def normalize_tradingview_symbol(symbol):
    """
    Normalizza il simbolo per TradingView.

    Caso importante:
    - BRK-B / BRK.B -> NYSE:BRK.B
    - BRK-A / BRK.A -> NYSE:BRK.A
    """
    symbol = clean_symbol(symbol)

    aliases = {
        "BRK-B": "NYSE:BRK.B",
        "BRK.B": "NYSE:BRK.B",
        "BRK/B": "NYSE:BRK.B",
        "NYSE:BRK-B": "NYSE:BRK.B",
        "NYSE:BRK.B": "NYSE:BRK.B",
        "BRK-A": "NYSE:BRK.A",
        "BRK.A": "NYSE:BRK.A",
        "BRK/A": "NYSE:BRK.A",
        "NYSE:BRK-A": "NYSE:BRK.A",
        "NYSE:BRK.A": "NYSE:BRK.A",
        "BF-B": "NYSE:BF.B",
        "BF.B": "NYSE:BF.B",
        "NYSE:BF-B": "NYSE:BF.B",
        "NYSE:BF.B": "NYSE:BF.B",
    }

    if symbol in aliases:
        return aliases[symbol]

    if ":" in symbol:
        return symbol

    if symbol.endswith(".MI"):
        return "MIL:" + symbol.replace(".MI", "")

    # Class shares USA generiche: ABC-B / ABC.B -> NYSE:ABC.B.
    if re.match(r"^[A-Z]{1,6}-[A-Z]$", symbol):
        base, klass = symbol.split("-", 1)
        return f"NYSE:{base}.{klass}"

    if re.match(r"^[A-Z]{1,6}\.[A-Z]$", symbol):
        return "NYSE:" + symbol

    nasdaq_symbols = {
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "NFLX", "ADBE",
        "AMD", "INTC", "CSCO", "AVGO", "QCOM", "TXN", "PEP", "COST", "AMAT", "MU",
        "PYPL", "SBUX", "ISRG", "BKNG", "LRCX", "PANW", "CRWD", "SHOP", "ARM", "SMCI"
    }

    nyse_symbols = {
        "JPM", "BAC", "V", "MA", "BRK.B", "BRK.A", "BRK-B", "BRK-A", "KO", "PG", "JNJ", "UNH", "HD",
        "DIS", "IBM", "ORCL", "CRM", "CVX", "XOM", "WMT", "MCD", "NKE", "CAT",
        "BA", "GS", "MS", "AXP", "GE", "T", "VZ", "PFE", "MRK", "LLY"
    }

    if symbol in nasdaq_symbols:
        return "NASDAQ:" + symbol

    if symbol in nyse_symbols:
        return "NYSE:" + symbol.replace("-", ".")

    return "NASDAQ:" + symbol


def simbolo_tradingview(symbol):
    """
    Conversione pratica Yahoo Finance -> TradingView per link esterno.

    Esempi:
    - AAPL      -> NASDAQ:AAPL
    - MSFT      -> NASDAQ:MSFT
    - JPM       -> NYSE:JPM
    - SWDA.MI   -> MIL:SWDA
    - BRK.B     -> NYSE:BRK.B
    - BRK-B     -> NYSE:BRK.B

    Se il simbolo contiene gia il mercato TradingView, viene mantenuto.
    """
    symbol = clean_symbol(symbol)

    if not symbol:
        return "NASDAQ:AAPL"

    return normalize_tradingview_symbol(symbol)


def url_tradingview(symbol):
    tv_symbol = simbolo_tradingview(symbol)
    return "https://www.tradingview.com/chart/?symbol=" + quote(tv_symbol, safe=":.")


def yfinance_to_tradingview_symbol(symbol: str) -> str:
    """Convert yfinance Milano symbols to TradingView format, e.g. 1AMZN.MI -> MIL:1AMZN."""
    clean_symbol = str(symbol or "").strip().upper()
    if not clean_symbol:
        return ""
    if ":" in clean_symbol:
        return clean_symbol
    if clean_symbol.endswith(".MI"):
        return "MIL:" + clean_symbol[:-3]
    return "NASDAQ:" + clean_symbol
