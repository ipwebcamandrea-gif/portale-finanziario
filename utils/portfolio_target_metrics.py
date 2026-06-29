from __future__ import annotations

import html
import math
from typing import Any

import pandas as pd

from utils.portfolio_formatting import fmt_num, value_class
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


def _currency_symbol(currency: str) -> str:
    clean_currency = _key(currency)
    return {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF"}.get(clean_currency, clean_currency)


def _signed_num(value: float, decimals: int = 2) -> str:
    return ("+" if value > 0 else "") + fmt_num(value, decimals)


def _signed_pct(value: float) -> str:
    return _signed_num(value, 2) + "%"


def _compact_signed_money(value: float, currency: str) -> str:
    numeric = float(value)
    sign = "+" if numeric > 0 else ""
    symbol = _currency_symbol(currency)
    abs_value = abs(numeric)
    if abs_value >= 1000:
        text = fmt_num(numeric / 1000.0, 1) + "k"
    else:
        text = fmt_num(numeric, 0)
    return sign + text + symbol


def _target_quote(value: float, currency: str) -> str:
    return fmt_num(value, 2) + _currency_symbol(currency)


def load_user_targets_map() -> dict[str, dict]:
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
    for candidate in (row.get("yf_symbol", ""), row.get("ticker", "")):
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
        rows.append({
            "label": label,
            "target": target_value,
            "gain_pct": gain_pct,
            "gain_currency": gain_currency,
            "gain_eur": gain_eur,
            "currency": currency,
            "css_class": value_class(gain_currency),
        })
    return rows


def render_target_desktop_html(row: pd.Series, target_item: dict | None) -> str:
    scenarios = _scenario_rows(row, target_item)
    if not scenarios:
        return '<div class="portfolio-target-cell portfolio-row-cell portfolio-target-empty">—</div>'
    lines = []
    for item in scenarios:
        eur_text = _compact_signed_money(item["gain_eur"], "EUR") if item.get("gain_eur") is not None else "€ n/d"
        lines.append(
            '<div class="portfolio-target-line ' + _esc(item["css_class"]) + '">'
            '<span class="portfolio-target-label">' + _esc(item["label"]) + '</span>'
            '<span class="portfolio-target-quote">' + _target_quote(item["target"], item["currency"]) + '</span>'
            '<span class="portfolio-target-pct">' + _signed_pct(item["gain_pct"]) + '</span>'
            '<span class="portfolio-target-money">'
            + _compact_signed_money(item["gain_currency"], item["currency"])
            + ' · '
            + eur_text
            + '</span>'
            '</div>'
        )
    return '<div class="portfolio-target-cell portfolio-row-cell">' + "".join(lines) + '</div>'


def _signed_money_eur(value: float | None) -> str:
    if value is None:
        return "€ n/d"
    sign = "+" if float(value) > 0 else ""
    return sign + fmt_num(float(value), 2) + " €"


def _mobile_cost_basis_price(row: pd.Series, target_item: dict | None = None) -> float | None:
    """Return the user's average load price used as the target tower baseline."""
    cost_basis = _safe_float(row.get("prezzo_medio"))
    if cost_basis is not None and cost_basis > 0:
        return cost_basis
    return None


def _mobile_current_market_price(row: pd.Series) -> float | None:
    """Return current market price for the orange marker, without adding another tower."""
    for key in ("prezzo_mercato", "last_price", "prezzo_corrente"):
        value = _safe_float(row.get(key))
        if value is not None and value > 0:
            return value
    return None


def _mobile_current_gain_eur(row: pd.Series, current_price: float | None) -> float | None:
    """Return current gain/loss in EUR vs average load price for mobile marker."""
    if current_price is None or current_price <= 0:
        return None

    cost_basis = _mobile_cost_basis_price(row)
    quantity = _safe_float(row.get("quantita"))
    currency = _key(row.get("valuta"))
    if cost_basis is None or cost_basis <= 0 or quantity is None or quantity <= 0:
        return None

    gain_currency = (float(current_price) - cost_basis) * quantity
    fx = convert_to_eur(gain_currency, currency)
    return _safe_float(fx.get("value")) if fx.get("ok") else None


def _mobile_target_scenarios(row: pd.Series, target_item: dict | None) -> list[dict]:
    if not target_item:
        return []

    cost_basis = _mobile_cost_basis_price(row, target_item)
    quantity = _safe_float(row.get("quantita"))
    currency = _key(row.get("valuta"))
    if cost_basis is None or cost_basis <= 0 or quantity is None or quantity <= 0:
        return []

    scenarios: list[dict] = [
        {
            "label": "CARICO",
            "target": cost_basis,
            "gain_pct": None,
            "gain_currency": None,
            "gain_eur": None,
            "currency": currency,
            "css_class": "portfolio-neutral",
            "is_current": True,
        }
    ]

    for field, label in TARGET_SCENARIOS:
        target_value = _safe_float(target_item.get(field))
        if target_value is None or target_value <= 0:
            continue
        gain_currency = (target_value - cost_basis) * quantity
        gain_pct = ((target_value - cost_basis) / cost_basis) * 100.0
        fx = convert_to_eur(gain_currency, currency)
        gain_eur = _safe_float(fx.get("value")) if fx.get("ok") else None
        scenarios.append(
            {
                "label": label,
                "target": target_value,
                "gain_pct": gain_pct,
                "gain_currency": gain_currency,
                "gain_eur": gain_eur,
                "currency": currency,
                "css_class": value_class(gain_currency),
                "is_current": False,
            }
        )
    return scenarios


def _mobile_target_chip_html(item: dict) -> str:
    if item.get("is_current"):
        pct_text = "prezzo"
        money_text = "carico"
        value_css = "portfolio-mobile-target-modern-neutral"
    else:
        pct_text = _signed_pct(item["gain_pct"])
        money_text = _signed_money_eur(item.get("gain_eur"))
        value_css = "portfolio-mobile-target-modern-positive" if (item.get("gain_eur") or 0.0) >= 0 else "portfolio-mobile-target-modern-negative"

    return (
        '<div class="portfolio-mobile-target-chip">'
        '<div class="portfolio-mobile-target-chip-label">' + _esc(item["label"]) + '</div>'
        '<div class="portfolio-mobile-target-chip-price">' + _target_quote(item["target"], item["currency"]) + '</div>'
        '<div class="portfolio-mobile-target-chip-pct ' + value_css + '">' + _esc(pct_text) + '</div>'
        '<div class="portfolio-mobile-target-chip-money ' + value_css + '">' + _esc(money_text) + '</div>'
        '</div>'
    )


def _mobile_tower_height_pct(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 12.0
    return max(12.0, min(100.0, (float(value) / max_value) * 100.0))


def _mobile_level_segment_html(current_height_pct: float | None) -> str:
    if current_height_pct is None:
        return ""
    return '<span class="portfolio-mobile-target-current-level-segment" style="bottom:' + fmt_num(current_height_pct, 1).replace(",", ".") + '%"></span>'


def _mobile_target_tower_html(item: dict, max_value: float, current_height_pct: float | None = None) -> str:
    height_pct = _mobile_tower_height_pct(float(item["target"]), max_value)
    bar_class = "portfolio-mobile-target-tower-bar-current" if item.get("is_current") else "portfolio-mobile-target-tower-bar-target"
    if not item.get("is_current") and item.get("gain_eur") is not None and item["gain_eur"] < 0:
        bar_class += " portfolio-mobile-target-tower-bar-negative"
    money_text = "" if item.get("is_current") else _signed_money_eur(item.get("gain_eur"))
    return (
        '<div class="portfolio-mobile-target-tower-item">'
        '<div class="portfolio-mobile-target-tower-value">' + _target_quote(item["target"], item["currency"]) + '</div>'
        '<div class="portfolio-mobile-target-tower-track">'
        '<div class="portfolio-mobile-target-tower-bar ' + bar_class + '" style="height:' + fmt_num(height_pct, 1).replace(",", ".") + '%"></div>'
        + _mobile_level_segment_html(current_height_pct) +
        '</div>'
        '<div class="portfolio-mobile-target-tower-label">' + _esc(item["label"]) + '</div>'
        '<div class="portfolio-mobile-target-tower-money">' + _esc(money_text) + '</div>'
        '</div>'
    )


def _mobile_current_marker_tower_html(current_price: float | None, max_value: float, currency: str, current_gain_eur: float | None = None) -> str:
    if current_price is None or current_price <= 0 or max_value <= 0:
        return ""

    height_pct = _mobile_tower_height_pct(float(current_price), max_value)
    gain_class = "portfolio-mobile-target-current-marker-money-positive" if (current_gain_eur or 0.0) >= 0 else "portfolio-mobile-target-current-marker-money-negative"
    gain_text = _signed_money_eur(current_gain_eur) if current_gain_eur is not None else ""
    return (
        '<div class="portfolio-mobile-target-tower-item portfolio-mobile-target-current-marker-item">'
        '<div class="portfolio-mobile-target-tower-value portfolio-mobile-target-current-marker-value">' + _target_quote(current_price, currency) + '</div>'
        '<div class="portfolio-mobile-target-tower-track portfolio-mobile-target-current-marker-track">'
        '<div class="portfolio-mobile-target-current-marker-linebar" style="height:' + fmt_num(height_pct, 1).replace(",", ".") + '%">'
        '<span class="portfolio-mobile-target-current-marker-dot"></span>'
        '</div>'
        + _mobile_level_segment_html(height_pct) +
        '</div>'
        '<div class="portfolio-mobile-target-tower-label portfolio-mobile-target-current-marker-label">Attuale</div>'
        '<div class="portfolio-mobile-target-tower-money portfolio-mobile-target-current-marker-money ' + gain_class + '">' + _esc(gain_text) + '</div>'
        '</div>'
    )


def render_target_mobile_html(row: pd.Series, target_item: dict | None) -> str:
    scenarios = _mobile_target_scenarios(row, target_item)
    if len(scenarios) <= 1:
        return ""

    current_price = _mobile_current_market_price(row)
    currency = _key(row.get("valuta"))
    current_gain_eur = _mobile_current_gain_eur(row, current_price)
    scale_values = [float(item["target"]) for item in scenarios]
    if current_price is not None and current_price > 0:
        scale_values.append(float(current_price))
    max_target = max(scale_values)
    current_height_pct = _mobile_tower_height_pct(float(current_price), max_target) if current_price is not None and current_price > 0 else None

    chips_html = "".join(_mobile_target_chip_html(item) for item in scenarios)
    tower_parts = []
    for index, item in enumerate(scenarios):
        tower_parts.append(_mobile_target_tower_html(item, max_target, current_height_pct))
        if index == 0:
            tower_parts.append(_mobile_current_marker_tower_html(current_price, max_target, currency, current_gain_eur))
    towers_html = "".join(tower_parts)

    return (
        '<div class="portfolio-mobile-target-modern-box">'
        '<div class="portfolio-mobile-target-modern-title">Target analisti · impatto posizione</div>'
        '<div class="portfolio-mobile-target-chip-grid">' + chips_html + '</div>'
        '<div class="portfolio-mobile-target-towers-title">Mini grafico target</div>'
        '<div class="portfolio-mobile-target-towers portfolio-mobile-target-towers-with-current">' + towers_html + '</div>'
        '<div class="portfolio-mobile-target-modern-note">€ stimati = (target - prezzo di carico) × quantità × cambio EUR</div>'
        '</div>'
    )


def enrich_portfolio_targets(df: pd.DataFrame) -> pd.DataFrame:
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
