from __future__ import annotations

from utils.portfolio_fx import convert_to_eur
from utils.portfolio_market_suggest import currency_for_market
from utils.portfolio_input_formatting import normalize_price, normalize_quantity
from utils.portfolio_prices import build_yfinance_symbol, fetch_last_quote
from utils.portfolio_tradingview import build_tradingview_symbol


DEFAULT_MARKET = "NASDAQ"


def _clean_text(value: str) -> str:
    return str(value or "").strip().upper()


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def fetch_position_title(yf_symbol: str, fallback_ticker: str) -> str:
    """Try to fetch a display name from yfinance; fallback to ticker."""
    clean_fallback = _clean_text(fallback_ticker)

    try:
        import yfinance as yf

        ticker_obj = yf.Ticker(yf_symbol)
        try:
            info = ticker_obj.get_info()
        except Exception:
            info = getattr(ticker_obj, "info", {}) or {}

        for key in ("shortName", "longName", "displayName", "symbol"):
            value = info.get(key)
            if value:
                return str(value).strip().upper()
    except Exception:
        pass

    return clean_fallback


def build_smart_position(
    ticker: str,
    mercato: str,
    valuta: str,
    quantita: float,
    prezzo_medio: float,
    titolo: str = "",
    yf_symbol: str = "",
    tv_symbol: str = "",
) -> dict:
    """Build a portfolio position from the minimal add form."""
    clean_ticker = _clean_text(ticker)
    clean_market = _clean_text(mercato) or DEFAULT_MARKET
    # Currency is derived from market to prevent inconsistent combinations such as MIL + USD.
    clean_currency = currency_for_market(clean_market)
    qty = normalize_quantity(quantita)
    avg_price = normalize_price(prezzo_medio)

    yf_symbol = build_yfinance_symbol(
        clean_ticker,
        clean_market,
        yf_symbol,
        clean_currency,
    )
    tv_symbol = build_tradingview_symbol(
        clean_market,
        clean_ticker,
        tv_symbol,
        clean_currency,
    )

    quote = fetch_last_quote(yf_symbol)
    quote_ok = bool(quote.get("ok"))
    market_price = float(quote.get("last")) if quote_ok else avg_price
    previous_price = float(quote.get("previous")) if quote_ok else avg_price

    title = str(titolo or "").strip() or fetch_position_title(yf_symbol, clean_ticker)

    invested_amount = qty * avg_price
    eur_conversion = convert_to_eur(invested_amount, clean_currency)

    position = {
        "ticker": clean_ticker,
        "titolo": title,
        "mercato": clean_market,
        "strumento": "Azione",
        "valuta": clean_currency,
        "quantita": qty,
        "prezzo_medio": avg_price,
        "prezzo_mercato": market_price,
        "prezzo_precedente": previous_price,
        "yf_symbol": yf_symbol,
        "tv_symbol": tv_symbol,
    }

    return {
        "position": position,
        "quote": quote,
        "quote_ok": quote_ok,
        "investment": {
            "amount": invested_amount,
            "currency": clean_currency,
            "eur_ok": eur_conversion.get("ok", False),
            "amount_eur": eur_conversion.get("value"),
            "fx_rate": eur_conversion.get("rate"),
            "fx_source": eur_conversion.get("source", ""),
            "fx_error": eur_conversion.get("error", ""),
        },
    }
