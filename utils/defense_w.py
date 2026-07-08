from __future__ import annotations

import math
from typing import Any

import pandas as pd


DEFENSE_W_HIGH_MAX_GAP_PCT = 7.5
DEFENSE_W_MEDIUM_MAX_GAP_PCT = 15.0
DEFENSE_W_PRICE_NEAR_ZONE_PCT = 10.0
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

    The level is intentionally calculated from the weekly price history only.
    It does not use options, DCF, targets, SMA200W or LinReg. For the first
    version of Area Difesa W we use the most visible structural floor: the
    lowest valid weekly low in the last 156 weeks, constrained to a sensible
    band below the current price when the current price is available.
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
        # collapse level too far away to be useful for a W area defense card.
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


def analyze_defense_w(
    *,
    current_price: float | None,
    weekly: pd.DataFrame | None,
    buy_zone_start: float | None,
) -> dict[str, Any]:
    """Analyze Area Difesa W.

    Area Difesa W compares an independent weekly technical support with the
    first real-options Buy Zone level (START). STRONG/PANIC are deliberately not
    used for the main convergence score.
    """
    support = technical_weekly_support(weekly, current_price=current_price)
    support_level = safe_float(support.get("support_w"))
    start = safe_float(buy_zone_start)
    price = safe_float(current_price)

    out: dict[str, Any] = {
        **support,
        "defense_w_available": False,
        "defense_w_active": False,
        "defense_w_state": "NO",
        "defense_w_convergence": "N/D",
        "defense_w_gap_pct": None,
        "defense_w_price_distance_pct": None,
        "defense_w_area_low": None,
        "defense_w_area_high": None,
        "defense_w_reason": "Servono supporto tecnico weekly e Buy Zone START opzioni.",
    }

    if support_level is None or support_level <= 0 or start is None or start <= 0:
        return out

    low = min(support_level, start)
    high = max(support_level, start)
    gap = abs(start - support_level) / start * 100.0
    price_distance = ((price - high) / high * 100.0) if price is not None and high > 0 else None

    if gap <= DEFENSE_W_HIGH_MAX_GAP_PCT:
        convergence = "Alta"
    elif gap <= DEFENSE_W_MEDIUM_MAX_GAP_PCT:
        convergence = "Media"
    else:
        convergence = "Bassa"

    price_near = price_distance is not None and price_distance <= DEFENSE_W_PRICE_NEAR_ZONE_PCT
    if convergence == "Alta" and price_near:
        state = "ATTIVO"
        active = True
        reason = "Supporto tecnico weekly e Buy Zone START sono vicini; il prezzo e' ancora vicino all'area combinata."
    elif convergence in {"Alta", "Media"}:
        state = "WATCH"
        active = False
        reason = "Esiste convergenza tra tecnica e opzioni, ma il prezzo non e' abbastanza vicino all'area combinata."
    else:
        state = "NO"
        active = False
        reason = "Supporto tecnico weekly e Buy Zone START sono troppo distanti."

    out.update({
        "defense_w_available": True,
        "defense_w_active": active,
        "defense_w_state": state,
        "defense_w_convergence": convergence,
        "defense_w_gap_pct": gap,
        "defense_w_price_distance_pct": price_distance,
        "defense_w_area_low": low,
        "defense_w_area_high": high,
        "defense_w_reason": reason,
    })
    return out
