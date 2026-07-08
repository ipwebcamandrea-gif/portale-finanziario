from __future__ import annotations

import math
from datetime import timedelta
from typing import Any

import pandas as pd
import yfinance as yf

SMA_WEEKS = 200
DEFAULT_MIN_RECOVERY_PCT = 40.0


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


def local_listing_underlying(yahoo_symbol: str) -> str | None:
    """Return a US underlying for local 1XXX.MI listings when safe.

    This is used only for Punto Ripartenza W / Anchor Low W. It must not be used
    as an options proxy for Buy Zone Avanzata.
    """
    symbol = str(yahoo_symbol or "").strip().upper()
    if symbol.startswith("1") and symbol.endswith(".MI") and len(symbol) > 4:
        core = symbol[1:-3].strip().upper()
        return core or None
    return None


def download_weekly(symbol: str) -> pd.DataFrame:
    try:
        return normalize_history(yf.download(symbol, period="20y", interval="1wk", auto_adjust=False, progress=False, threads=False))
    except Exception:
        return pd.DataFrame()


def download_daily_window(symbol: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    try:
        start = (pd.to_datetime(start_date) - timedelta(days=7)).strftime("%Y-%m-%d")
        end = (pd.to_datetime(end_date) + timedelta(days=14)).strftime("%Y-%m-%d")
        return normalize_history(yf.download(symbol, start=start, end=end, interval="1d", auto_adjust=False, progress=False, threads=False))
    except Exception:
        return pd.DataFrame()


def eurusd_rate_for_date(date_value: str | pd.Timestamp) -> float | None:
    try:
        dt = pd.to_datetime(date_value)
        fx = normalize_history(yf.download("EURUSD=X", start=(dt - timedelta(days=3)).strftime("%Y-%m-%d"), end=(dt + timedelta(days=5)).strftime("%Y-%m-%d"), interval="1d", auto_adjust=False, progress=False, threads=False))
        if fx.empty or "Close" not in fx.columns:
            return None
        fx = fx.dropna(subset=["Close"])
        if fx.empty:
            return None
        # Use the nearest available FX close to the anchor date.
        idx = min(fx.index, key=lambda x: abs((pd.to_datetime(x).date() - dt.date()).days))
        return safe_float(fx.loc[idx, "Close"])
    except Exception:
        return None


def find_last_under_sma200w_episode(weekly: pd.DataFrame | None, current_price: float | None = None) -> dict[str, Any]:
    """Find the latest meaningful under-SMA200W reset and its lowest weekly low."""
    out = {
        "available": False,
        "weekly_low": None,
        "weekly_date": None,
        "episode_start": None,
        "episode_end": None,
        "recovery_pct": None,
        "reason": "Nessuna fase sotto SMA200W disponibile.",
    }
    w = normalize_history(weekly)
    if w.empty or not {"Close", "Low"}.issubset(w.columns):
        out["reason"] = "Storico weekly incompleto."
        return out
    h = w.copy().dropna(subset=["Close", "Low"])
    h = h[(pd.to_numeric(h["Close"], errors="coerce") > 0) & (pd.to_numeric(h["Low"], errors="coerce") > 0)]
    if len(h) < SMA_WEEKS:
        out["reason"] = f"Storico insufficiente per SMA200W: {len(h)} settimane."
        return out
    close = pd.to_numeric(h["Close"], errors="coerce")
    low = pd.to_numeric(h["Low"], errors="coerce")
    h["SMA200W"] = close.rolling(SMA_WEEKS).mean()
    h = h.dropna(subset=["SMA200W"])
    if h.empty:
        return out
    under = pd.to_numeric(h["Low"], errors="coerce") < pd.to_numeric(h["SMA200W"], errors="coerce")
    if not bool(under.any()):
        out["reason"] = "Il titolo non ha avuto Low weekly sotto SMA200W nel periodo disponibile."
        return out

    episodes: list[tuple[int, int]] = []
    start = None
    under_values = under.tolist()
    for i, flag in enumerate(under_values):
        if flag and start is None:
            start = i
        if start is not None and ((not flag) or i == len(under_values) - 1):
            end = i if flag and i == len(under_values) - 1 else i - 1
            episodes.append((start, end))
            start = None

    candidates = []
    current = safe_float(current_price)
    for start_i, end_i in episodes:
        seg = h.iloc[start_i:end_i + 1]
        if seg.empty:
            continue
        min_idx = pd.to_numeric(seg["Low"], errors="coerce").idxmin()
        min_low = safe_float(seg.loc[min_idx, "Low"])
        if min_low is None or min_low <= 0:
            continue
        # A valid current-cycle anchor cannot be above the current price.
        # If price has already broken below that low, the supposed restart is invalid
        # and we must look for an earlier W restart point.
        if current is not None and current > 0 and min_low > current * 1.001:
            continue
        after = h.loc[min_idx:]
        max_after = safe_float(pd.to_numeric(after["Close"], errors="coerce").max())
        recovery = ((max_after - min_low) / min_low * 100.0) if max_after is not None and min_low else None
        candidates.append({
            "start_i": start_i,
            "end_i": end_i,
            "weekly_low": min_low,
            "weekly_date": min_idx,
            "episode_start": h.index[start_i],
            "episode_end": h.index[end_i],
            "recovery_pct": recovery,
        })

    if not candidates:
        out["reason"] = "Nessun anchor valido: le fasi sotto SMA200W trovate sono sopra il prezzo attuale o non sono utilizzabili."
        return out

    # Do not simply take the last under-SMA200W episode: a recent small pullback
    # can go marginally below SMA200W but is not a true W restart point.
    # We require a meaningful subsequent recovery. Then we take the latest
    # confirmed restart. This keeps MSFT/1MSFT.MI anchored to Jan 2023 instead
    # of a recent shallow 2026 correction.
    confirmed = [
        c for c in candidates
        if safe_float(c.get("recovery_pct")) is not None
        and float(c["recovery_pct"]) >= DEFAULT_MIN_RECOVERY_PCT
    ]
    chosen = confirmed[-1] if confirmed else max(
        candidates,
        key=lambda c: safe_float(c.get("recovery_pct"), -999.0) or -999.0,
    )
    out.update({
        "available": True,
        "weekly_low": chosen["weekly_low"],
        "weekly_date": chosen["weekly_date"],
        "episode_start": chosen["episode_start"],
        "episode_end": chosen["episode_end"],
        "recovery_pct": chosen["recovery_pct"],
        "reason": "Ultima fase sotto SMA200W con ripartenza W significativa.",
    })
    return out


def refine_anchor_with_daily(symbol: str, episode_start: pd.Timestamp, episode_end: pd.Timestamp, fallback_low: float | None, fallback_date: pd.Timestamp | None) -> dict[str, Any]:
    out = {"low": fallback_low, "date": fallback_date, "close": None}
    daily = download_daily_window(symbol, pd.to_datetime(episode_start), pd.to_datetime(episode_end))
    if daily.empty or "Low" not in daily.columns:
        return out
    d = daily.copy().dropna(subset=["Low"])
    d = d[pd.to_numeric(d["Low"], errors="coerce") > 0]
    if d.empty:
        return out
    idx = pd.to_numeric(d["Low"], errors="coerce").idxmin()
    out["low"] = safe_float(d.loc[idx, "Low"])
    out["date"] = idx
    if "Close" in d.columns:
        out["close"] = safe_float(d.loc[idx, "Close"])
    return out


def empty_anchor(reason: str) -> dict[str, Any]:
    return {
        "anchor_w_available": False,
        "anchor_w_price": None,
        "anchor_w_date": None,
        "anchor_w_close": None,
        "anchor_w_distance_pct": None,
        "anchor_w_recovery_pct": None,
        "anchor_w_method": "N/D",
        "anchor_w_source_symbol": None,
        "anchor_w_source_price": None,
        "anchor_w_source_close": None,
        "anchor_w_source_currency": None,
        "anchor_w_converted": False,
        "anchor_w_fx_rate": None,
        "anchor_w_note": reason,
    }


def analyze_anchor_low_w(
    yahoo_symbol: str,
    *,
    current_price: float | None = None,
    currency: str = "",
    weekly: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Calculate Punto Ripartenza W / Anchor Low W.

    The point is the low of the latest meaningful under-SMA200W weekly reset.
    For local listings such as 1MSFT.MI, the technical anchor is found on the
    underlying MSFT and converted to the local currency when FX data is available.
    """
    symbol = str(yahoo_symbol or "").strip().upper()
    cur = str(currency or "").strip().upper()
    if not symbol:
        return empty_anchor("Ticker mancante.")

    source_symbol = local_listing_underlying(symbol) or symbol
    converted = source_symbol != symbol
    method = "Sottostante convertito" if converted else "Ticker diretto"
    source_currency = "USD" if converted else cur

    source_weekly = download_weekly(source_symbol) if converted else weekly
    episode = find_last_under_sma200w_episode(source_weekly, current_price=None if converted else current_price)
    if not episode.get("available"):
        reason = str(episode.get("reason") or "Punto Ripartenza W non disponibile.")
        if converted:
            reason = f"Sottostante {source_symbol}: {reason}"
        return empty_anchor(reason)

    daily_anchor = refine_anchor_with_daily(
        source_symbol,
        pd.to_datetime(episode.get("episode_start")),
        pd.to_datetime(episode.get("episode_end")),
        safe_float(episode.get("weekly_low")),
        pd.to_datetime(episode.get("weekly_date")),
    )
    source_low = safe_float(daily_anchor.get("low") or episode.get("weekly_low"))
    source_close = safe_float(daily_anchor.get("close"))
    anchor_date_obj = pd.to_datetime(daily_anchor.get("date") or episode.get("weekly_date"))
    anchor_date = anchor_date_obj.strftime("%Y-%m-%d") if hasattr(anchor_date_obj, "strftime") else str(anchor_date_obj)
    anchor_price = source_low
    fx_rate = None

    note = "Minimo sotto SMA200W da cui e' partito il ciclo W rialzista."
    if converted and source_low is not None:
        if cur == "EUR":
            fx_rate = eurusd_rate_for_date(anchor_date_obj)
            if fx_rate is not None and fx_rate > 0:
                anchor_price = source_low / fx_rate
                note = f"Calcolato sul sottostante {source_symbol} e convertito in EUR. Non usato come proxy opzioni."
            else:
                note = f"Calcolato sul sottostante {source_symbol}; cambio storico non disponibile, mostrato valore fonte."
        else:
            note = f"Calcolato sul sottostante {source_symbol}; valuta locale non EUR/non disponibile."

    price_now = safe_float(current_price)
    distance = ((price_now - anchor_price) / anchor_price * 100.0) if price_now is not None and anchor_price not in (None, 0) else None

    return {
        "anchor_w_available": anchor_price is not None and anchor_price > 0,
        "anchor_w_price": anchor_price,
        "anchor_w_date": anchor_date,
        "anchor_w_close": None if converted else source_close,
        "anchor_w_distance_pct": distance,
        "anchor_w_recovery_pct": episode.get("recovery_pct"),
        "anchor_w_method": method,
        "anchor_w_source_symbol": source_symbol,
        "anchor_w_source_price": source_low,
        "anchor_w_source_close": source_close,
        "anchor_w_source_currency": source_currency,
        "anchor_w_converted": converted and fx_rate is not None,
        "anchor_w_fx_rate": fx_rate,
        "anchor_w_note": note,
    }
