from __future__ import annotations

import math
from typing import Any

import pandas as pd


DEFENSE_W_HIGH_MAX_GAP_PCT = 7.5
DEFENSE_W_MEDIUM_MAX_GAP_PCT = 15.0
DEFENSE_W_ACTIVE_MAX_DISTANCE_PCT = 10.0
DEFENSE_W_WATCH_MAX_DISTANCE_PCT = 20.0
DEFENSE_W_LOOKBACK_WEEKS = 156


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


def normalize_weekly(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        if "Low" in out.columns.get_level_values(0):
            out.columns = out.columns.get_level_values(0)
        elif "Low" in out.columns.get_level_values(-1):
            out.columns = out.columns.get_level_values(-1)
    return out.dropna(how="all")


def technical_weekly_support(weekly: pd.DataFrame | None, current_price: float | None = None) -> dict[str, Any]:
    """Return an independent weekly technical support level.

    This support is calculated only from weekly price history. It does not use
    options, DCF, targets, SMA200W or LinReg, so Area Difesa W remains available
    even when option chains are not returned by yfinance/Streamlit Cloud.
    """
    out: dict[str, Any] = {
        "support_w": None,
        "support_w_date": None,
        "support_w_method": "Minimo weekly strutturale 156 settimane",
        "support_w_note": "Supporto tecnico weekly non disponibile.",
    }
    h = normalize_weekly(weekly)
    if h.empty or "Low" not in h.columns:
        return out

    lows = pd.to_numeric(h["Low"], errors="coerce").dropna()
    lows = lows[lows > 0]
    if lows.empty:
        return out

    window = lows.tail(min(len(lows), DEFENSE_W_LOOKBACK_WEEKS))
    price = safe_float(current_price)
    if price is not None and price > 0:
        # Keep the support technically relevant: below spot, but not an old
        # collapse level too far away to be useful for a W defense card.
        filtered = window[(window <= price * 0.995) & (window >= price * 0.50)]
        if not filtered.empty:
            window = filtered

    idx = window.idxmin()
    support = safe_float(window.loc[idx])
    if support is None or support <= 0:
        return out

    date_text = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
    out.update({
        "support_w": float(support),
        "support_w_date": date_text,
        "support_w_note": f"Minimo weekly nel lookback: {date_text}",
    })
    return out


def option_convergence_with_support(support_level: float | None, buy_zone_start: float | None) -> dict[str, Any]:
    """Optional convergence between technical support and options START.

    This is informational only. It must not decide whether Area Difesa W exists
    or whether the fifth motivation is active.
    """
    support = safe_float(support_level)
    start = safe_float(buy_zone_start)
    out: dict[str, Any] = {
        "defense_w_option_convergence": "N/D",
        "defense_w_option_gap_pct": None,
        "defense_w_option_reason": "Buy Zone START opzioni non disponibile.",
    }
    if support is None or support <= 0 or start is None or start <= 0:
        return out

    gap = abs(start - support) / start * 100.0
    if gap <= DEFENSE_W_HIGH_MAX_GAP_PCT:
        convergence = "Alta"
    elif gap <= DEFENSE_W_MEDIUM_MAX_GAP_PCT:
        convergence = "Media"
    else:
        convergence = "Bassa"
    out.update({
        "defense_w_option_convergence": convergence,
        "defense_w_option_gap_pct": gap,
        "defense_w_option_reason": "Confronto opzionale tra supporto tecnico W e Buy Zone START opzioni.",
    })
    return out


def analyze_defense_w(
    *,
    current_price: float | None,
    weekly: pd.DataFrame | None,
    buy_zone_start: float | None = None,
) -> dict[str, Any]:
    """Analyze Area Difesa W as a pure technical signal.

    Main Area Difesa W uses only the weekly technical support and current price.
    Options START is used only as optional context when available.
    """
    support = technical_weekly_support(weekly, current_price=current_price)
    support_level = safe_float(support.get("support_w"))
    price = safe_float(current_price)

    out: dict[str, Any] = {
        **support,
        "defense_w_available": False,
        "defense_w_active": False,
        "defense_w_state": "NO",
        "defense_w_convergence": "TECNICA",
        "defense_w_gap_pct": None,
        "defense_w_price_distance_pct": None,
        "defense_w_area_low": None,
        "defense_w_area_high": None,
        "defense_w_reason": "Serve uno storico weekly valido per calcolare il supporto tecnico W.",
        "defense_w_option_convergence": "N/D",
        "defense_w_option_gap_pct": None,
        "defense_w_option_reason": "Buy Zone START opzioni non disponibile.",
    }

    if support_level is None or support_level <= 0:
        return out

    price_distance = ((price - support_level) / support_level * 100.0) if price is not None and support_level > 0 else None
    if price_distance is not None and price_distance <= DEFENSE_W_ACTIVE_MAX_DISTANCE_PCT:
        state = "ATTIVO"
        active = True
        reason = "Prezzo entro il +10% dal supporto tecnico weekly."
    elif price_distance is not None and price_distance <= DEFENSE_W_WATCH_MAX_DISTANCE_PCT:
        state = "WATCH"
        active = False
        reason = "Prezzo tra +10% e +20% dal supporto tecnico weekly."
    elif price_distance is not None:
        state = "NO"
        active = False
        reason = "Prezzo oltre il +20% dal supporto tecnico weekly."
    else:
        state = "WATCH"
        active = False
        reason = "Supporto tecnico weekly disponibile, ma prezzo attuale non disponibile."

    out.update({
        "defense_w_available": True,
        "defense_w_active": active,
        "defense_w_state": state,
        "defense_w_convergence": "TECNICA",
        "defense_w_gap_pct": price_distance,
        "defense_w_price_distance_pct": price_distance,
        "defense_w_area_low": support_level,
        "defense_w_area_high": support_level,
        "defense_w_reason": reason,
    })
    out.update(option_convergence_with_support(support_level, buy_zone_start))
    return out
