from __future__ import annotations

from functools import lru_cache
import re

LOOKUP_MARKETS = ["NASDAQ", "NYSE", "MIL"]
US_MARKETS = {"NASDAQ", "NYSE"}
MARKET_DISPLAY_NAMES = {"NASDAQ": "NASDAQ", "NYSE": "NYSE", "MIL": "Milano"}
MARKET_CURRENCY = {"NASDAQ": "USD", "NYSE": "USD", "MIL": "EUR"}

SECURITY_MASTER = {
    "AAPL": {"name": "Apple Inc.", "market": "NASDAQ", "aliases": ["APPLE"]},
    "MSFT": {"name": "Microsoft Corporation", "market": "NASDAQ", "aliases": ["MICROSOFT"]},
    "AMZN": {"name": "Amazon.com, Inc.", "market": "NASDAQ", "aliases": ["AMAZON"]},
    "GOOGL": {"name": "Alphabet Inc.", "market": "NASDAQ", "aliases": ["GOOGLE", "ALPHABET"]},
    "GOOG": {"name": "Alphabet Inc.", "market": "NASDAQ", "aliases": ["GOOGLE CLASS C"]},
    "NVDA": {"name": "NVIDIA Corporation", "market": "NASDAQ", "aliases": ["NVIDIA"]},
    "META": {"name": "Meta Platforms, Inc.", "market": "NASDAQ", "aliases": ["META", "FACEBOOK"]},
    "TSLA": {"name": "Tesla, Inc.", "market": "NASDAQ", "aliases": ["TESLA"]},
    "NFLX": {"name": "Netflix, Inc.", "market": "NASDAQ", "aliases": ["NETFLIX"]},
    "AMD": {"name": "Advanced Micro Devices, Inc.", "market": "NASDAQ", "aliases": ["ADVANCED MICRO DEVICES"]},
    "INTC": {"name": "Intel Corporation", "market": "NASDAQ", "aliases": ["INTEL"]},
    "AVGO": {"name": "Broadcom Inc.", "market": "NASDAQ", "aliases": ["BROADCOM"]},
    "PEP": {"name": "PepsiCo, Inc.", "market": "NASDAQ", "aliases": ["PEPSI", "PEPSICO"]},
    "COST": {"name": "Costco Wholesale Corporation", "market": "NASDAQ", "aliases": ["COSTCO"]},
    "ADBE": {"name": "Adobe Inc.", "market": "NASDAQ", "aliases": ["ADOBE"]},
    "PYPL": {"name": "PayPal Holdings, Inc.", "market": "NASDAQ", "aliases": ["PAYPAL"]},
    "SBUX": {"name": "Starbucks Corporation", "market": "NASDAQ", "aliases": ["STARBUCKS"]},
    "SOFI": {"name": "SoFi Technologies, Inc.", "market": "NASDAQ", "aliases": ["SOFI"]},
    "MSTR": {"name": "MicroStrategy Incorporated", "market": "NASDAQ", "aliases": ["MICROSTRATEGY"]},
    "PLTR": {"name": "Palantir Technologies Inc.", "market": "NASDAQ", "aliases": ["PALANTIR"]},
    "JPM": {"name": "JPMorgan Chase & Co.", "market": "NYSE", "aliases": ["JPMORGAN", "JP MORGAN"]},
    "BAC": {"name": "Bank of America Corporation", "market": "NYSE", "aliases": ["BANK OF AMERICA"]},
    "V": {"name": "Visa Inc.", "market": "NYSE", "aliases": ["VISA"]},
    "MA": {"name": "Mastercard Incorporated", "market": "NYSE", "aliases": ["MASTERCARD"]},
    "BRK.B": {"name": "Berkshire Hathaway Inc.", "market": "NYSE", "aliases": ["BERKSHIRE", "BERKSHIRE HATHAWAY"]},
    "KO": {"name": "The Coca-Cola Company", "market": "NYSE", "aliases": ["COCA COLA", "COCA-COLA", "COCACOLA"]},
    "PG": {"name": "The Procter & Gamble Company", "market": "NYSE", "aliases": ["PROCTER", "PROCTER GAMBLE", "P&G"]},
    "JNJ": {"name": "Johnson & Johnson", "market": "NYSE", "aliases": ["JOHNSON"]},
    "UNH": {"name": "UnitedHealth Group Incorporated", "market": "NYSE", "aliases": ["UNITEDHEALTH", "UNITED HEALTH"]},
    "HD": {"name": "The Home Depot, Inc.", "market": "NYSE", "aliases": ["HOME DEPOT"]},
    "DIS": {"name": "The Walt Disney Company", "market": "NYSE", "aliases": ["DISNEY", "WALT DISNEY"]},
    "IBM": {"name": "International Business Machines Corporation", "market": "NYSE", "aliases": ["IBM"]},
    "ORCL": {"name": "Oracle Corporation", "market": "NYSE", "aliases": ["ORACLE"]},
    "CRM": {"name": "Salesforce, Inc.", "market": "NYSE", "aliases": ["SALESFORCE"]},
    "XOM": {"name": "Exxon Mobil Corporation", "market": "NYSE", "aliases": ["EXXON", "EXXON MOBIL"]},
    "CVX": {"name": "Chevron Corporation", "market": "NYSE", "aliases": ["CHEVRON"]},
    "WMT": {"name": "Walmart Inc.", "market": "NYSE", "aliases": ["WALMART"]},
    "MCD": {"name": "McDonald's Corporation", "market": "NYSE", "aliases": ["MCDONALD", "MCDONALDS"]},
    "NKE": {"name": "NIKE, Inc.", "market": "NYSE", "aliases": ["NIKE"]},
    "LLY": {"name": "Eli Lilly and Company", "market": "NYSE", "aliases": ["ELI LILLY", "LILLY"]},
    "UBER": {"name": "Uber Technologies, Inc.", "market": "NYSE", "aliases": ["UBER"]},
    "ENEL": {"name": "Enel S.p.A.", "market": "MIL", "aliases": ["ENEL"]},
    "ENI": {"name": "Eni S.p.A.", "market": "MIL", "aliases": ["ENI"]},
    "ISP": {"name": "Intesa Sanpaolo S.p.A.", "market": "MIL", "aliases": ["INTESA", "INTESA SANPAOLO"]},
    "UCG": {"name": "UniCredit S.p.A.", "market": "MIL", "aliases": ["UNICREDIT", "UNICREDIT SPA"]},
    "RACE": {"name": "Ferrari N.V.", "market": "MIL", "aliases": ["FERRARI"]},
    "STLAM": {"name": "Stellantis N.V.", "market": "MIL", "aliases": ["STELLANTIS"]},
    "TIT": {"name": "Telecom Italia S.p.A.", "market": "MIL", "aliases": ["TELECOM ITALIA", "TIM"]},
    "PST": {"name": "Poste Italiane S.p.A.", "market": "MIL", "aliases": ["POSTE", "POSTE ITALIANE"]},
    "G": {"name": "Assicurazioni Generali S.p.A.", "market": "MIL", "aliases": ["GENERALI", "ASSICURAZIONI GENERALI"]},
}

YFINANCE_EXCHANGE_TO_MARKET = {
    "NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ", "NASDAQ": "NASDAQ",
    "NASDAQGS": "NASDAQ", "NASDAQGM": "NASDAQ", "NASDAQCM": "NASDAQ",
    "NYQ": "NYSE", "NYSE": "NYSE", "NYE": "NYSE",
    "MIL": "MIL", "MILAN": "MIL",
}


def normalize_query(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().upper())


def clean_ticker(value: str) -> str:
    return normalize_query(value).replace(" ", "")


def _strip_market_prefix(value: str) -> tuple[str, str]:
    text = normalize_query(value)
    if ":" not in text:
        return "", text
    market, symbol = text.split(":", 1)
    market = market.strip().upper()
    symbol = symbol.strip().upper()
    if market == "BIT":
        market = "MIL"
    if market not in LOOKUP_MARKETS:
        market = ""
    return market, symbol


def _base_from_milan_symbol(symbol: str) -> str:
    clean_symbol = clean_ticker(symbol)
    if clean_symbol.endswith(".MI"):
        clean_symbol = clean_symbol[:-3]
    return clean_symbol


def _milan_symbol_for_us_ticker(us_ticker: str) -> str:
    ticker = clean_ticker(us_ticker)
    if ticker.endswith(".MI"):
        return ticker
    if ticker.startswith("1"):
        return f"{ticker}.MI"
    return f"1{ticker}.MI"


def _tradingview_symbol(market: str, ticker: str) -> str:
    clean_market = normalize_query(market) or "NASDAQ"
    ticker_clean = clean_ticker(ticker)
    if clean_market == "MIL":
        if ticker_clean.endswith(".MI"):
            ticker_clean = ticker_clean[:-3]
        return f"MIL:{ticker_clean}"
    return f"{clean_market}:{ticker_clean}"


def _candidate(*, ticker: str, name: str, market: str, yf_symbol: str, tv_symbol: str, source: str, confidence: str = "medium") -> dict:
    clean_market = normalize_query(market) or "NASDAQ"
    ticker_clean = clean_ticker(ticker)
    currency = MARKET_CURRENCY.get(clean_market, "USD")
    label = f"{yf_symbol} · {name or ticker_clean} · {MARKET_DISPLAY_NAMES.get(clean_market, clean_market)} · {currency}"
    return {
        "key": f"{clean_market}|{yf_symbol}|{tv_symbol}",
        "ticker": ticker_clean,
        "name": str(name or ticker_clean).strip(),
        "market": clean_market,
        "currency": currency,
        "yf_symbol": yf_symbol,
        "tv_symbol": tv_symbol,
        "label": label,
        "source": source,
        "confidence": confidence,
    }


@lru_cache(maxsize=512)
def fetch_yfinance_identity(yf_symbol: str) -> dict:
    symbol = clean_ticker(yf_symbol)
    if not symbol:
        return {}
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).get_info() or {}
        name = info.get("shortName") or info.get("longName") or info.get("displayName") or info.get("symbol") or ""
        exchange = str(info.get("exchange") or "").strip().upper()
        return {"name": str(name or "").strip(), "exchange": exchange, "market": YFINANCE_EXCHANGE_TO_MARKET.get(exchange, "")}
    except Exception:
        return {}


def _known_security_for_query(query: str) -> tuple[str, dict | None]:
    q = normalize_query(query)
    q_compact = clean_ticker(q)
    if not q:
        return "", None
    if q_compact in SECURITY_MASTER:
        return q_compact, SECURITY_MASTER[q_compact]
    for ticker, data in SECURITY_MASTER.items():
        name = normalize_query(data.get("name", ""))
        aliases = [normalize_query(a) for a in data.get("aliases", [])]
        haystack = [name, *aliases]
        if q in haystack or q_compact in [clean_ticker(a) for a in haystack]:
            return ticker, data
        if len(q) >= 3 and any(q in item for item in haystack):
            return ticker, data
    return "", None


def _add_unique(candidates: list[dict], candidate: dict) -> None:
    if candidate.get("key") and not any(item.get("key") == candidate.get("key") for item in candidates):
        candidates.append(candidate)


def _build_candidates_for_known(ticker: str, data: dict, include_milan: bool = True) -> list[dict]:
    primary_market = data.get("market") or "NASDAQ"
    name = data.get("name") or ticker
    candidates: list[dict] = []
    if primary_market in US_MARKETS:
        _add_unique(candidates, _candidate(ticker=ticker, name=name, market=primary_market, yf_symbol=ticker, tv_symbol=_tradingview_symbol(primary_market, ticker), source="local_master", confidence="high"))
        if include_milan:
            mil_yf = _milan_symbol_for_us_ticker(ticker)
            mil_ticker = _base_from_milan_symbol(mil_yf)
            _add_unique(candidates, _candidate(ticker=mil_ticker, name=name, market="MIL", yf_symbol=mil_yf, tv_symbol=_tradingview_symbol("MIL", mil_ticker), source="local_master_mil_equivalent", confidence="medium"))
    elif primary_market == "MIL":
        yf_symbol = ticker if ticker.endswith(".MI") else f"{ticker}.MI"
        mil_ticker = _base_from_milan_symbol(yf_symbol)
        _add_unique(candidates, _candidate(ticker=mil_ticker, name=name, market="MIL", yf_symbol=yf_symbol, tv_symbol=_tradingview_symbol("MIL", mil_ticker), source="local_master_mil", confidence="high"))
    return candidates


def search_ticker_candidates(query: str, *, include_milan_equivalent: bool = True) -> list[dict]:
    raw_query = normalize_query(query)
    if not raw_query:
        return []
    explicit_market, raw_symbol = _strip_market_prefix(raw_query)
    symbol = clean_ticker(raw_symbol)
    candidates: list[dict] = []

    if explicit_market == "MIL" or symbol.endswith(".MI") or symbol.startswith("1"):
        mil_ticker = _base_from_milan_symbol(symbol)
        yf_symbol = mil_ticker if mil_ticker.endswith(".MI") else f"{mil_ticker}.MI"
        known_key = mil_ticker[1:] if mil_ticker.startswith("1") else mil_ticker
        identity = fetch_yfinance_identity(yf_symbol)
        known = SECURITY_MASTER.get(known_key, {})
        name = identity.get("name") or known.get("name") or mil_ticker
        _add_unique(candidates, _candidate(ticker=mil_ticker, name=name, market="MIL", yf_symbol=yf_symbol, tv_symbol=_tradingview_symbol("MIL", mil_ticker), source="explicit_mil", confidence="high"))
        return candidates

    known_ticker, known_data = _known_security_for_query(raw_query)
    if known_data:
        return _build_candidates_for_known(known_ticker, known_data, include_milan=include_milan_equivalent)

    if not re.fullmatch(r"[A-Z0-9.]{1,12}", symbol):
        return []

    identity = fetch_yfinance_identity(symbol)
    inferred_market = identity.get("market") or explicit_market or "NASDAQ"
    if inferred_market not in US_MARKETS:
        inferred_market = "NASDAQ"
    name = identity.get("name") or symbol
    _add_unique(candidates, _candidate(ticker=symbol, name=name, market=inferred_market, yf_symbol=symbol, tv_symbol=_tradingview_symbol(inferred_market, symbol), source="ticker_fallback", confidence="medium" if identity else "low"))

    if include_milan_equivalent:
        mil_yf = _milan_symbol_for_us_ticker(symbol)
        mil_ticker = _base_from_milan_symbol(mil_yf)
        mil_identity = fetch_yfinance_identity(mil_yf)
        _add_unique(candidates, _candidate(ticker=mil_ticker, name=mil_identity.get("name") or name, market="MIL", yf_symbol=mil_yf, tv_symbol=_tradingview_symbol("MIL", mil_ticker), source="ticker_fallback_mil_equivalent", confidence="low"))
    return candidates


def format_candidate_label(candidate: dict | None) -> str:
    return str((candidate or {}).get("label") or "").strip()


def get_candidate_by_key(candidates: list[dict], key: str) -> dict | None:
    for candidate in candidates:
        if candidate.get("key") == key:
            return candidate
    return None
