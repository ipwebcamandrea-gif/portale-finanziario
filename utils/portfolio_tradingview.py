US_PRIMARY_MARKETS = {"NASDAQ", "NYSE", "AMEX", "ARCA"}


def infer_eur_tv_symbol(ticker: str, mercato: str, valuta: str) -> str:
    """Infer the TradingView EUR listing for US stocks traded on Borsa Italiana.

    Example:
    MSFT / NASDAQ / EUR -> MIL:1MSFT
    """
    clean_ticker = str(ticker or "").strip().upper()
    clean_market = str(mercato or "").strip().upper()
    clean_currency = str(valuta or "").strip().upper()

    if clean_currency != "EUR":
        return ""

    if clean_market not in US_PRIMARY_MARKETS:
        return ""

    if not clean_ticker:
        return ""

    if clean_ticker.startswith("1"):
        return f"MIL:{clean_ticker}"

    return f"MIL:1{clean_ticker}"


def build_tradingview_symbol(
    mercato: str,
    ticker: str,
    tv_symbol: str = "",
    valuta: str = "",
) -> str:
    """Build a TradingView symbol such as NASDAQ:MSFT or MIL:1MSFT.

    Priority:
    1. explicit `tv_symbol` from CSV/form;
    2. inferred EUR listing for US stocks traded in EUR;
    3. fallback `{mercato}:{ticker}`.
    """
    clean_tv_symbol = str(tv_symbol or "").strip().upper()
    if clean_tv_symbol:
        return clean_tv_symbol

    inferred_eur_symbol = infer_eur_tv_symbol(ticker, mercato, valuta)
    if inferred_eur_symbol:
        return inferred_eur_symbol

    clean_market = str(mercato or "").strip().upper()
    clean_ticker = str(ticker or "").strip().upper()

    if not clean_market:
        clean_market = "NASDAQ"

    return f"{clean_market}:{clean_ticker}"
