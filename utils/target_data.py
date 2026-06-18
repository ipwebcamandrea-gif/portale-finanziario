from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from utils.portfolio_prices import fetch_last_quote
from utils.portfolio_tradingview import build_tradingview_symbol


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean_symbol(value: str) -> str:
    return str(value or "").strip().upper()


def _to_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _info_value(info: dict, *keys: str):
    for key in keys:
        if key in info and info.get(key) not in (None, ""):
            return info.get(key)
    return None


def fetch_yfinance_targets(yf_symbol: str, *, ticker: str = "", market: str = "", currency: str = "", tv_symbol: str = "") -> dict[str, Any]:
    """Fetch analyst targets from yfinance without inventing missing values."""
    clean_yf = _clean_symbol(yf_symbol)
    if not clean_yf:
        return {"ok": False, "error": "Simbolo yfinance vuoto"}
    try:
        import yfinance as yf
        info = yf.Ticker(clean_yf).get_info() or {}
    except Exception as exc:
        return {"ok": False, "error": f"Target yfinance non disponibili: {exc}"}

    target_low = _to_float(_info_value(info, "targetLowPrice", "target_low_price"))
    target_mean = _to_float(_info_value(info, "targetMeanPrice", "target_mean_price", "targetMedianPrice"))
    target_high = _to_float(_info_value(info, "targetHighPrice", "target_high_price"))
    analyst_count = _info_value(info, "numberOfAnalystOpinions", "numberOfAnalystOpinions")
    rating = _info_value(info, "recommendationKey", "recommendationMean")
    name = _info_value(info, "shortName", "longName", "displayName", "symbol") or clean_yf

    if target_low is None and target_mean is None and target_high is None:
        return {"ok": False, "error": "yfinance non espone target analisti per questo simbolo"}

    exchange_currency = str(_info_value(info, "currency") or currency or "").upper()
    clean_market = str(market or "").upper()
    if not clean_market:
        exchange = str(_info_value(info, "exchange") or "").upper()
        clean_market = {"NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ", "NYQ": "NYSE", "MIL": "MIL"}.get(exchange, "")
    if not tv_symbol:
        tv_symbol = build_tradingview_symbol(clean_market or "NASDAQ", ticker or clean_yf.replace(".MI", ""), "", exchange_currency)

    quote = fetch_last_quote(clean_yf)
    current_price = _to_float(quote.get("last")) if quote.get("ok") else None

    return {
        "ok": True,
        "source": "yfinance",
        "yf_symbol": clean_yf,
        "ticker": _clean_symbol(ticker) or clean_yf.replace(".MI", ""),
        "tv_symbol": tv_symbol,
        "name": str(name),
        "market": clean_market,
        "currency": exchange_currency or currency or "USD",
        "current_price": current_price,
        "target_low": target_low,
        "target_mean": target_mean,
        "target_high": target_high,
        "analyst_count": analyst_count,
        "rating": str(rating or ""),
        "updated_at": now_iso(),
    }
