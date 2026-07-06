from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf


DEFAULT_DAYS = [30, 90, 180]
BUYZONE_TOLERANCE_PCT = 5.0

DCF_PARAMS = {
    "MSFT": {"r": 0.085, "decline_rate": 0.08, "tv_multiple": 14},
    "AAPL": {"r": 0.085, "decline_rate": 0.10, "tv_multiple": 13},
    "GOOGL": {"r": 0.090, "decline_rate": 0.10, "tv_multiple": 12},
    "GOOG": {"r": 0.090, "decline_rate": 0.10, "tv_multiple": 12},
    "META": {"r": 0.095, "decline_rate": 0.12, "tv_multiple": 11},
    "AMZN": {"r": 0.095, "decline_rate": 0.08, "tv_multiple": 13},
    "NVDA": {"r": 0.105, "decline_rate": 0.18, "tv_multiple": 16},
    "TSLA": {"r": 0.110, "decline_rate": 0.25, "tv_multiple": 10},
}
DEFAULT_DCF_PARAMS = {"r": 0.095, "decline_rate": 0.12, "tv_multiple": 11}


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        x = float(value)
        if pd.isna(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def median_or_none(values: list[float | None]) -> float | None:
    vals = [safe_float(v) for v in values]
    vals = [float(v) for v in vals if v is not None and v > 0]
    if not vals:
        return None
    return float(np.median(vals))


def percentile_or_none(values: list[float | None], pct: float) -> float | None:
    vals = [safe_float(v) for v in values]
    vals = [float(v) for v in vals if v is not None and v > 0]
    if not vals:
        return None
    return float(np.percentile(vals, pct))


def normalize_history(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        if "Close" in out.columns.get_level_values(0):
            out.columns = out.columns.get_level_values(0)
        elif "Close" in out.columns.get_level_values(-1):
            out.columns = out.columns.get_level_values(-1)
    return out.dropna(how="all")


def nearest_expiration(dates: list[str], target_days: int) -> str | None:
    if not dates:
        return None
    today = datetime.now(timezone.utc).date()
    best = None
    best_diff = None
    for item in dates:
        try:
            exp = pd.to_datetime(item).date()
        except Exception:
            continue
        diff = abs((exp - today).days - target_days)
        if best is None or diff < best_diff:
            best = item
            best_diff = diff
    return best


def option_put_wall(ticker_obj: yf.Ticker, date_str: str, price: float | None) -> tuple[float | None, int | None, str]:
    p = safe_float(price)
    if p is None or p <= 0:
        return None, None, "prezzo non disponibile"
    try:
        chain = ticker_obj.option_chain(date_str)
        puts = chain.puts.copy()
    except Exception as exc:
        return None, None, f"opzioni non disponibili: {exc}"
    if puts is None or puts.empty or "strike" not in puts.columns:
        return None, None, "put non disponibili"
    puts["strike"] = pd.to_numeric(puts["strike"], errors="coerce")
    puts = puts.dropna(subset=["strike"])
    puts = puts[(puts["strike"] < p) & (puts["strike"] >= p * 0.60) & (puts["strike"] <= p * 0.98)]
    if puts.empty:
        return None, None, "nessuna put sotto prezzo nel range"
    for col in ("openInterest", "volume", "bid", "ask"):
        if col not in puts.columns:
            puts[col] = 0
        puts[col] = pd.to_numeric(puts[col], errors="coerce").fillna(0)
    spread_penalty = (puts["ask"] - puts["bid"]).clip(lower=0)
    puts["score"] = puts["openInterest"] * 1.0 + puts["volume"] * 0.35 - spread_penalty * 10.0
    puts = puts.sort_values(["score", "openInterest", "volume"], ascending=False)
    row = puts.iloc[0]
    strike = safe_float(row.get("strike"))
    oi = int(safe_float(row.get("openInterest"), 0) or 0)
    return strike, oi, "put wall stimata da open interest/volume"


def option_walls(ticker_obj: yf.Ticker, price: float | None, days_list: list[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    try:
        dates = list(ticker_obj.options or [])
    except Exception:
        dates = []
    for days in days_list:
        exp = nearest_expiration(dates, days)
        if not exp:
            out[days] = {"expiration": None, "put_wall": None, "put_wall_oi": None, "note": "scadenza opzioni non disponibile"}
            continue
        wall, oi, note = option_put_wall(ticker_obj, exp, price)
        out[days] = {"expiration": exp, "put_wall": wall, "put_wall_oi": oi, "note": note}
    return out


def cashflow_value(frame: pd.DataFrame | None, keys: list[str]) -> float | None:
    if frame is None or frame.empty:
        return None
    for key in keys:
        if key in frame.index:
            vals = pd.to_numeric(frame.loc[key], errors="coerce").dropna()
            if not vals.empty:
                return safe_float(vals.iloc[0])
    return None


def compute_dcf_bear_per_share(ticker_obj: yf.Ticker, info: dict[str, Any], symbol: str) -> float | None:
    try:
        cf = ticker_obj.cashflow
    except Exception:
        cf = pd.DataFrame()
    operating_cf = cashflow_value(cf, ["Operating Cash Flow", "Total Cash From Operating Activities"])
    capex = cashflow_value(cf, ["Capital Expenditure", "Capital Expenditures"])
    if operating_cf is None:
        return None
    fcf0 = operating_cf + (capex or 0.0)
    shares = safe_float(info.get("sharesOutstanding") or info.get("impliedSharesOutstanding"))
    if fcf0 is None or fcf0 <= 0 or shares is None or shares <= 0:
        return None
    cash = safe_float(info.get("totalCash"), 0.0) or 0.0
    debt = safe_float(info.get("totalDebt"), 0.0) or 0.0
    params = DCF_PARAMS.get(str(symbol or "").upper().replace("-", "."), DEFAULT_DCF_PARAMS)
    r = float(params["r"])
    decline = float(params["decline_rate"])
    multiple = float(params["tv_multiple"])
    pv = 0.0
    fcf = float(fcf0)
    for year in range(1, 6):
        fcf = fcf * (1.0 - decline)
        pv += fcf / ((1.0 + r) ** year)
    terminal = max(fcf, 0.0) * multiple
    pv += terminal / ((1.0 + r) ** 5)
    equity = pv + cash - debt
    if equity <= 0:
        return None
    return equity / shares


def technical_levels_from_history(hist: pd.DataFrame | None, weekly: pd.DataFrame | None = None) -> dict[str, float | None]:
    out = {"low_3m": None, "low_6m": None, "low_12m": None, "sma50": None, "sma200": None, "atr14": None}
    h = normalize_history(hist)
    if h.empty and weekly is not None:
        h = normalize_history(weekly)
    if h.empty or "Close" not in h.columns:
        return out
    close = pd.to_numeric(h["Close"], errors="coerce").dropna()
    if close.empty:
        return out
    low_source = pd.to_numeric(h["Low"], errors="coerce") if "Low" in h.columns else close
    low_source = low_source.dropna()
    if not low_source.empty:
        out["low_3m"] = safe_float(low_source.tail(63).min())
        out["low_6m"] = safe_float(low_source.tail(126).min())
        out["low_12m"] = safe_float(low_source.tail(252).min())
    if len(close) >= 50:
        out["sma50"] = safe_float(close.tail(50).mean())
    if len(close) >= 200:
        out["sma200"] = safe_float(close.tail(200).mean())
    if {"High", "Low", "Close"}.issubset(h.columns) and len(h) >= 15:
        high = pd.to_numeric(h["High"], errors="coerce")
        low = pd.to_numeric(h["Low"], errors="coerce")
        prev_close = pd.to_numeric(h["Close"], errors="coerce").shift(1)
        tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        out["atr14"] = safe_float(tr.tail(14).mean())
    return out


def compute_buy_zones(price: float | None, technical: dict[str, float | None], walls: dict[int, dict[str, Any]], dcf_bear: float | None, linreg_lower: float | None = None, sma200w: float | None = None) -> dict[str, float | None]:
    wall30 = safe_float(walls.get(30, {}).get("put_wall"))
    wall90 = safe_float(walls.get(90, {}).get("put_wall"))
    wall180 = safe_float(walls.get(180, {}).get("put_wall"))
    low3 = safe_float(technical.get("low_3m"))
    low6 = safe_float(technical.get("low_6m"))
    low12 = safe_float(technical.get("low_12m"))
    sma200 = safe_float(technical.get("sma200")) or safe_float(sma200w)
    lower = safe_float(linreg_lower)
    atr = safe_float(technical.get("atr14"))

    start = median_or_none([low3, low6, sma200, lower, wall30])
    strong = median_or_none([low6, low12, lower, wall90, wall180, dcf_bear])
    panic_candidates = [low12, wall180, dcf_bear]
    if low12 is not None and atr is not None:
        panic_candidates.append(low12 - 1.5 * atr)
    if dcf_bear is not None:
        panic_candidates.append(dcf_bear * 0.90)
    panic = percentile_or_none(panic_candidates, 25)

    # Keep the zones logically ordered when enough values are available.
    if start is not None and strong is not None and strong > start:
        start, strong = strong, start
    if strong is not None and panic is not None and panic > strong:
        panic = strong * 0.92

    return {"buy_zone_start": start, "buy_zone_strong": strong, "panic_zone": panic}


def confidence_note(technical: dict[str, float | None], walls: dict[int, dict[str, Any]], dcf_bear: float | None) -> tuple[str, str]:
    score = 0
    notes: list[str] = []
    if any(safe_float(technical.get(k)) is not None for k in ("low_3m", "low_6m", "low_12m", "sma200")):
        score += 1
        notes.append("tecnico")
    if any(safe_float(item.get("put_wall")) is not None for item in walls.values()):
        score += 1
        notes.append("put wall")
    if safe_float(dcf_bear) is not None:
        score += 1
        notes.append("DCF bear")
    label = "Alta" if score >= 3 else "Media" if score == 2 else "Bassa" if score == 1 else "N/D"
    if notes:
        return label, ", ".join(notes) + " disponibili per il modello avanzato."
    return label, "Dati avanzati non sufficienti per una stima robusta."


def buyzone_signal(price: float | None, start: float | None, strong: float | None, panic: float | None, tolerance_pct: float = BUYZONE_TOLERANCE_PCT) -> dict[str, Any]:
    p = safe_float(price)
    if p is None or p <= 0:
        return {"active": False, "zone": None, "label": "Buy Zone Avanzate N/D", "reason": "Prezzo non disponibile per valutare le buy zone avanzate.", "distance_pct": None}

    def near(level: float | None) -> tuple[bool, float | None]:
        lv = safe_float(level)
        if lv is None or lv <= 0:
            return False, None
        dist = (p - lv) / lv * 100.0
        return abs(dist) <= tolerance_pct, dist

    for key, label, reason in [
        ("panic_zone", "Prezzo nell'intorno della Panic Zone", "il prezzo attuale e' entro il +/-5% dalla zona estrema stimata dal modello avanzato."),
        ("buy_zone_strong", "Prezzo nell'intorno della Strong Buy Zone", "il prezzo attuale e' entro il +/-5% dalla zona di accumulo piu' interessante calcolata dal modello avanzato."),
        ("buy_zone_start", "Prezzo nell'intorno della Buy Zone Start", "il prezzo attuale e' entro il +/-5% dalla prima area operativa calcolata dal modello avanzato."),
    ]:
        level = {"panic_zone": panic, "buy_zone_strong": strong, "buy_zone_start": start}[key]
        ok, dist = near(level)
        if ok:
            return {"active": True, "zone": key, "label": label, "reason": reason, "distance_pct": dist}
    return {"active": False, "zone": None, "label": "Fuori Buy Zone Avanzate", "reason": "il prezzo attuale non e' entro il +/-5% da Start, Strong o Panic Zone.", "distance_pct": None}


def analyze_advanced_buy_zone(symbol: str, current_price: float | None = None, currency: str = "", weekly: pd.DataFrame | None = None, linreg_lower: float | None = None, sma200w: float | None = None, days_list: list[int] | None = None) -> dict[str, Any]:
    days_list = days_list or DEFAULT_DAYS
    out: dict[str, Any] = {
        "advanced_buyzone_available": False,
        "advanced_buyzone_error": "",
        "buy_zone_start": None,
        "buy_zone_strong": None,
        "panic_zone": None,
        "advanced_confidence": "N/D",
        "advanced_confidence_note": "Dati avanzati non disponibili.",
        "advanced_signal_active": False,
        "advanced_signal_zone": None,
        "advanced_signal_label": "Buy Zone Avanzate N/D",
        "advanced_signal_reason": "Dati avanzati non disponibili.",
        "dcf_bear": None,
        "put_wall_30": None,
        "put_wall_90": None,
        "put_wall_180": None,
    }
    yf_symbol = str(symbol or "").strip().upper()
    if not yf_symbol:
        out["advanced_buyzone_error"] = "ticker mancante"
        return out
    try:
        ticker_obj = yf.Ticker(yf_symbol)
        hist = normalize_history(ticker_obj.history(period="2y", auto_adjust=True))
        price = safe_float(current_price)
        if price is None and not hist.empty and "Close" in hist.columns:
            price = safe_float(hist["Close"].dropna().iloc[-1])
        technical = technical_levels_from_history(hist, weekly)
        walls = option_walls(ticker_obj, price, days_list)
        info = {}
        try:
            info = ticker_obj.get_info()
        except Exception:
            try:
                info = ticker_obj.info
            except Exception:
                info = {}
        if not isinstance(info, dict):
            info = {}
        dcf = compute_dcf_bear_per_share(ticker_obj, info, yf_symbol)
        zones = compute_buy_zones(price, technical, walls, dcf, linreg_lower=linreg_lower, sma200w=sma200w)
        conf, note = confidence_note(technical, walls, dcf)
        signal = buyzone_signal(price, zones.get("buy_zone_start"), zones.get("buy_zone_strong"), zones.get("panic_zone"))
        out.update(zones)
        out.update({
            "advanced_buyzone_available": any(safe_float(zones.get(k)) is not None for k in ("buy_zone_start", "buy_zone_strong", "panic_zone")),
            "advanced_confidence": conf,
            "advanced_confidence_note": note,
            "advanced_signal_active": bool(signal.get("active")),
            "advanced_signal_zone": signal.get("zone"),
            "advanced_signal_label": signal.get("label"),
            "advanced_signal_reason": signal.get("reason"),
            "advanced_signal_distance_pct": signal.get("distance_pct"),
            "dcf_bear": dcf,
        })
        for days in days_list:
            out[f"put_wall_{days}"] = safe_float(walls.get(days, {}).get("put_wall"))
        return out
    except Exception as exc:
        out["advanced_buyzone_error"] = str(exc)
        return out
