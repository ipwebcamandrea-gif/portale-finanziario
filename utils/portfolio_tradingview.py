def build_tradingview_symbol(mercato: str, ticker: str, tv_symbol: str = "") -> str:
    """Build a TradingView symbol such as NASDAQ:MSFT or MIL:1MSFT.

    If `tv_symbol` is provided in the portfolio CSV, it wins. This is important
    for EUR listings, where the portfolio position may refer to a local European
    instrument and not to the USD primary listing.
    """
    clean_tv_symbol = str(tv_symbol or "").strip().upper()
    if clean_tv_symbol:
        return clean_tv_symbol

    clean_market = str(mercato or "").strip().upper()
    clean_ticker = str(ticker or "").strip().upper()

    if not clean_market:
        clean_market = "NASDAQ"

    return f"{clean_market}:{clean_ticker}"
