from __future__ import annotations

import math

import streamlit as st


DIRECT_FX_SYMBOLS = {
    "USD": "USDEUR=X",
    "GBP": "GBPEUR=X",
    "CHF": "CHFEUR=X",
}

INVERSE_FX_SYMBOLS = {
    "USD": "EURUSD=X",
    "GBP": "EURGBP=X",
    "CHF": "EURCHF=X",
}

SUPPORTED_CURRENCIES = {"EUR", "USD", "GBP", "CHF"}


def _clean_currency(currency: str) -> str:
    return str(currency or "").strip().upper()


def _valid_rate(value) -> bool:
    try:
        numeric = float(value)
        return math.isfinite(numeric) and numeric > 0
    except Exception:
        return False


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_yfinance_last_price(symbol: str) -> dict:
    """Fetch a last price from yfinance for FX symbols."""
    if not symbol:
        return {"ok": False, "price": None, "error": "Simbolo cambio vuoto"}

    try:
        import yfinance as yf
    except Exception as exc:
        return {"ok": False, "price": None, "error": f"yfinance non disponibile: {exc}"}

    try:
        ticker = yf.Ticker(symbol)

        try:
            fast_info = ticker.fast_info
            price = fast_info.get("last_price") or fast_info.get("lastPrice")
            if _valid_rate(price):
                return {"ok": True, "price": float(price), "error": ""}
        except Exception:
            pass

        hist = ticker.history(period="5d", interval="1d", auto_adjust=False)
        if hist is not None and not hist.empty and "Close" in hist.columns:
            close_values = hist["Close"].dropna()
            if not close_values.empty:
                price = float(close_values.iloc[-1])
                if _valid_rate(price):
                    return {"ok": True, "price": price, "error": ""}

        return {"ok": False, "price": None, "error": "Cambio non disponibile"}
    except Exception as exc:
        return {"ok": False, "price": None, "error": str(exc)}


@st.cache_data(ttl=900, show_spinner=False)
def get_fx_to_eur(currency: str) -> dict:
    """Return the FX rate from a currency to EUR.

    No fake 1.0 fallback is used for non-EUR currencies. If yfinance cannot
    provide a rate, `ok` is False.
    """
    clean_currency = _clean_currency(currency)

    if clean_currency == "EUR":
        return {
            "ok": True,
            "currency": "EUR",
            "rate": 1.0,
            "source": "EUR",
            "error": "",
        }

    if clean_currency not in SUPPORTED_CURRENCIES:
        return {
            "ok": False,
            "currency": clean_currency,
            "rate": None,
            "source": "",
            "error": f"Valuta non supportata: {clean_currency}",
        }

    direct_symbol = DIRECT_FX_SYMBOLS.get(clean_currency, "")
    direct = _fetch_yfinance_last_price(direct_symbol)
    if direct.get("ok") and _valid_rate(direct.get("price")):
        return {
            "ok": True,
            "currency": clean_currency,
            "rate": float(direct["price"]),
            "source": direct_symbol,
            "error": "",
        }

    inverse_symbol = INVERSE_FX_SYMBOLS.get(clean_currency, "")
    inverse = _fetch_yfinance_last_price(inverse_symbol)
    if inverse.get("ok") and _valid_rate(inverse.get("price")):
        return {
            "ok": True,
            "currency": clean_currency,
            "rate": 1.0 / float(inverse["price"]),
            "source": f"1/{inverse_symbol}",
            "error": "",
        }

    return {
        "ok": False,
        "currency": clean_currency,
        "rate": None,
        "source": direct_symbol or inverse_symbol,
        "error": direct.get("error") or inverse.get("error") or "Cambio non disponibile",
    }


def get_fx_rates_to_eur(currencies) -> tuple[dict, dict]:
    """Return `(rates, errors)` for all requested currencies."""
    rates = {}
    errors = {}

    for currency in sorted({_clean_currency(item) for item in currencies if str(item or "").strip()}):
        result = get_fx_to_eur(currency)
        if result.get("ok"):
            rates[currency] = float(result["rate"])
        else:
            errors[currency] = result.get("error", "Cambio non disponibile")

    return rates, errors


def convert_to_eur(amount: float, currency: str) -> dict:
    """Convert an amount to EUR using yfinance FX rates."""
    try:
        numeric_amount = float(amount)
    except Exception:
        return {"ok": False, "value": None, "rate": None, "source": "", "error": "Importo non valido"}

    fx = get_fx_to_eur(currency)
    if not fx.get("ok"):
        return {"ok": False, "value": None, "rate": None, "source": fx.get("source", ""), "error": fx.get("error", "Cambio non disponibile")}

    rate = float(fx["rate"])
    return {
        "ok": True,
        "value": numeric_amount * rate,
        "rate": rate,
        "source": fx.get("source", ""),
        "error": "",
    }
