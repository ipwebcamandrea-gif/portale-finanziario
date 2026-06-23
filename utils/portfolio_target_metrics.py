from __future__ import annotations

import html
import math
from typing import Any

import pandas as pd

from utils.portfolio_formatting import fmt_eur, fmt_num, value_class
from utils.portfolio_fx import convert_to_eur
from utils.target_storage import load_targets
from utils.user_paths import get_user_targets_path


TARGET_SCENARIOS = (
    ("target_low", "Min"),
    ("target_mean", "Med"),
    ("target_high", "Max"),
)


def _key(value: Any) -> str:
    return str(value or "").strip().upper()


def _safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except Exception:
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _signed_num(value: float, decimals: int = 2) -> str:
    prefix = "+" if value > 0 else ""
    return prefix + fmt_num(value, decimals)


def _signed_pct(value: float) -> str:
    return _signed_num(value, 2) + "%"


def _signed_money(value: float, currency: str) -> str:
    clean_currency = _key(currency)
    suffix = f" {clean_currency}" if clean_currency else ""
    return _signed_num(value, 2) + suffix


def load_user_targets_map() -> dict[str, dict]:
    """Load current user's saved analyst targets keyed by yfinance symbol."""
    try:
        payload = load_targets(get_user_targets_path())
    except Exception:
        return {}

    raw_targets = payload.get("targets", {}) if isinstance(payload, dict) else {}
    if not isinstance(raw_targets, dict):
        return {}

    result: dict[str, dict] = {}
    for raw_key, item in raw_targets.items():
        if isinstance(item, dict):
            clean_key = _key(item.get("yf_symbol") or raw_key)
            if clean_key:
                result[clean_key] = item
    return result


def _find_target_item(row: pd.Series, targets: dict[str, dict]) -> dict | None:
    candidates = [
        row.get("yf_symbol", ""),
        row.get("ticker", ""),
    ]
    for candidate in candidates:
        clean = _key(candidate)
        if clean and clean in targets:
            return targets[clean]
    return None


def _scenario_rows(row: pd.Series, target_item: dict | None) -> list[dict]:
    if not target_item:
        return []

    avg_price = _safe_float(row.get("prezzo_medio"))
    quantity = _safe_float(row.get("quantita"))
    currency = _key(row.get("valuta"))

    if avg_price is None or avg_price <= 0 or quantity is None or quantity <= 0:
        return []

    rows: list[dict] = []
    for field, label in TARGET_SCENARIOS:
        target_value = _safe_float(target_item.get(field))
        if target_value is None or target_value <= 0:
            continue

        gain_currency = (target_value - avg_price) * quantity
        gain_pct = ((target_value - avg_price) / avg_price) * 100.0
        fx = convert_to_eur(gain_currency, currency)
        gain_eur = _safe_float(fx.get("value")) if fx.get("ok") else None

        rows.append(
            {
                "label": label,
                "target": target_value,
                "gain_pct": gain_pct,
                "gain_currency": gain_currency,
                "gain_eur": gain_eur,
                "currency": currency,
                "css_class": value_class(gain_currency),
            }
        )
    return rows


def render_target_desktop_html(row: pd.Series, target_item: dict | None) -> str:
    scenarios = _scenario_rows(row, target_item)
    if not scenarios:
        return '<div class="portfolio-target-cell portfolio-row-cell portfolio-target-empty">—</div>'

    lines = []
    for item in scenarios:
        eur_text = _signed_money(item["gain_eur"], "EUR") if item.get("gain_eur") is not None else "EUR n/d"
        lines.append(
            '<div class="portfolio-target-line ' + _esc(item["css_class"]) + '">'
            '<span class="portfolio-target-label">' + _esc(item["label"]) + '</span>'
            '<span class="portfolio-target-pct">' + _signed_pct(item["gain_pct"]) + '</span>'
            '<span class="portfolio-target-money">'
            + _signed_money(item["gain_currency"], item["currency"])
            + ' / '
            + eur_text
            + '</span>'
            '</div>'
        )

    return '<div class="portfolio-target-cell portfolio-row-cell">' + "".join(lines) + '</div>'


def render_target_mobile_html(row: pd.Series, target_item: dict | None) -> str:
    scenarios = _scenario_rows(row, target_item)
    if not scenarios:
        return ""

    lines = []
    for item in scenarios:
        eur_text = _signed_money(item["gain_eur"], "EUR") if item.get("gain_eur") is not None else "EUR n/d"
        lines.append(
            '<div class="portfolio-mobile-target-line ' + _esc(item["css_class"]) + '">'
            '<span class="portfolio-mobile-target-label">' + _esc(item["label"]) + '</span>'
            '<span class="portfolio-mobile-target-values">'
            + _signed_pct(item["gain_pct"])
            + ' · '
            + _signed_money(item["gain_currency"], item["currency"])
            + ' · '
            + eur_text
            + '</span>'
            '</div>'
        )

    return (
        '<div class="portfolio-mobile-target-box">'
        '<div class="portfolio-mobile-target-title">Target da carico</div>'
        + "".join(lines)
        + '</div>'
    )


def enrich_portfolio_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Add HTML target scenario columns to a portfolio dataframe.

    Calculations are based on the user's average load price (`prezzo_medio`), not
    on the current market price. The source is the current user's
    `target_analisti.json`.
    """
    if df is None or df.empty:
        return df

    result = df.copy()
    targets = load_user_targets_map()

    desktop_html = []
    mobile_html = []
    for _, row in result.iterrows():
        target_item = _find_target_item(row, targets)
        desktop_html.append(render_target_desktop_html(row, target_item))
        mobile_html.append(render_target_mobile_html(row, target_item))

    result["portfolio_target_desktop_html"] = desktop_html
    result["portfolio_target_mobile_html"] = mobile_html
    return result
