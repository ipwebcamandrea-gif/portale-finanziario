from __future__ import annotations

from typing import Any

# =========================
# STIME OPERATIVE SMA200W
# =========================
# Queste fasce sono stime operative fisse, non dati calcolati in tempo reale.
# Servono come riferimento accanto alla distanza attuale dalla SMA200W.
# Per renderle dinamiche servirebbe calcolarle dallo storico weekly di ogni titolo.

SMA200_ESTIMATED_RANGES: dict[str, dict[str, str]] = {
    "SWDA.MI": {"below": "-20% / -30%", "above": "+20% / +35%"},
    "ACWI": {"below": "-20% / -30%", "above": "+20% / +35%"},
    "SPY": {"below": "-18% / -28%", "above": "+20% / +35%"},
    "1MSFT.MI": {"below": "-8% / -16%", "above": "+25% / +45%"},
    "TSLA": {"below": "-40% / -60%", "above": "+70% / +140%"},
    "COST": {"below": "-8% / -15%", "above": "+20% / +35%"},
    "MSFT": {"below": "-10% / -20%", "above": "+30% / +55%"},
    "V": {"below": "-10% / -20%", "above": "+25% / +45%"},
    "MA": {"below": "-10% / -20%", "above": "+25% / +45%"},
    "ORCL": {"below": "-12% / -22%", "above": "+35% / +65%"},
    "PG": {"below": "-8% / -15%", "above": "+15% / +30%"},
    "JNJ": {"below": "-10% / -18%", "above": "+15% / +30%"},
    "KO": {"below": "-8% / -15%", "above": "+15% / +30%"},
    "PEP": {"below": "-8% / -16%", "above": "+15% / +30%"},
    "MCD": {"below": "-10% / -18%", "above": "+20% / +35%"},
    "ABT": {"below": "-10% / -20%", "above": "+20% / +40%"},
    "PFE": {"below": "-20% / -35%", "above": "+20% / +45%"},
    "WMT": {"below": "-8% / -15%", "above": "+20% / +35%"},
    "AAPL": {"below": "-15% / -28%", "above": "+35% / +65%"},
    "GOOG": {"below": "-15% / -30%", "above": "+35% / +65%"},
    "BRK.B": {"below": "-12% / -22%", "above": "+20% / +40%"},
    "NVDA": {"below": "-35% / -55%", "above": "+80% / +180%"},
    "ASML": {"below": "-25% / -45%", "above": "+45% / +90%"},
    "META": {"below": "-30% / -50%", "above": "+60% / +130%"},
    "JPM": {"below": "-20% / -35%", "above": "+30% / +60%"},
    "BLK": {"below": "-20% / -35%", "above": "+30% / +60%"},
    "IBM": {"below": "-15% / -28%", "above": "+25% / +50%"},
    "AVGO": {"below": "-25% / -45%", "above": "+60% / +130%"},
    "HD": {"below": "-18% / -32%", "above": "+25% / +50%"},
    "AXP": {"below": "-25% / -40%", "above": "+35% / +70%"},
    "AMZN": {"below": "-25% / -45%", "above": "+50% / +100%"},
    "CRM": {"below": "-30% / -45%", "above": "+45% / +90%"},
}


def _normalize_symbol(symbol: Any) -> str:
    clean = str(symbol or "").strip().upper()
    if clean == "BRK-B":
        return "BRK.B"
    return clean


def get_sma200_estimate(symbol: Any) -> dict[str, str] | None:
    return SMA200_ESTIMATED_RANGES.get(_normalize_symbol(symbol))


def get_sma200_estimate_label(symbol: Any) -> str:
    item = get_sma200_estimate(symbol)
    if not item:
        return ""
    return "↓ " + item["below"] + " · ↑ " + item["above"]
