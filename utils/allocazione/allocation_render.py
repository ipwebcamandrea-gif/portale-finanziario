from __future__ import annotations

import math
from html import escape

import streamlit as st

from utils.allocazione.allocation_charts import create_position_bar, create_position_donut
from utils.allocazione.portfolio_allocation import concentration_class, concentration_label
from utils.portfolio_formatting import fmt_eur, fmt_pct, value_class
from utils.portfolio_target_metrics import load_user_targets_map


TARGET_FIELDS = (
    ("cost_basis", "Carico", "Prezzo di carico"),
    ("target_low", "Min", "Target minimo"),
    ("target_mean", "Med", "Target medio"),
    ("target_high", "Max", "Target massimo"),
)


def render_page_header() -> None:
    st.markdown('<div class="allocation-page-title">📊 Allocazione Portafoglio</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="allocation-page-subtitle">Distribuzione attuale per titolo, valuta, mercato e concentrazione. Tutti i titoli sono sempre visibili.</div>',
        unsafe_allow_html=True,
    )


def _summary_card(label: str, value: str, subtitle: str = "") -> None:
    html = (
        '<div class="allocation-summary-card">'
        f'<div class="allocation-summary-label">{escape(str(label))}</div>'
        f'<div class="allocation-summary-value">{escape(str(value))}</div>'
        f'<div class="allocation-summary-subtitle">{escape(str(subtitle))}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _allocation_display_symbol(row) -> str:
    display_symbol = str(row.get("display_symbol", "") or "").strip().upper()
    if display_symbol:
        return display_symbol

    market = str(row.get("mercato", "") or "").strip().upper()
    ticker = str(row.get("ticker", "") or "").strip().upper()
    if market and ticker:
        return f"{market}:{ticker}"
    return ticker or market or "-"


def _key(value) -> str:
    return str(value or "").strip().upper()


def _safe_float(value, default: float | None = None) -> float | None:
    try:
        numeric = float(value)
        if math.isfinite(numeric):
            return numeric
    except Exception:
        pass
    return default


def _currency_suffix(currency: str) -> str:
    currency = _key(currency)
    if currency == "EUR":
        return "€"
    if currency == "USD":
        return "$"
    return currency or ""


def _format_price(value: float | None, currency: str) -> str:
    if value is None:
        return "—"
    suffix = _currency_suffix(currency)
    if suffix in {"€", "$"}:
        return f"{value:,.2f}{suffix}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{value:,.2f} {suffix}".replace(",", "X").replace(".", ",").replace("X", ".").strip()


def _format_signed_pct(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return (sign + f"{value:.2f}%").replace(".", ",")


def _current_market_price(row) -> float | None:
    """Return the current market price used by allocation concentration cards."""
    for key in ("prezzo_mercato", "last_price", "prezzo_corrente"):
        value = _safe_float(row.get(key))
        if value is not None and value > 0:
            return value
    return None


def _render_current_price_box(row) -> str:
    """Render a flexible current-price mini card for allocation concentration only."""
    current_price = _current_market_price(row)
    if current_price is None:
        return ""

    currency = _key(row.get("valuta"))
    daily_pct = _safe_float(row.get("var_quotidiana_pct"))
    daily_class = "allocation-current-price-positive" if (daily_pct or 0.0) >= 0 else "allocation-current-price-negative"
    daily_text = _format_signed_pct(daily_pct) if daily_pct is not None else "—"

    return (
        '<div class="allocation-current-price-box">'
        '<div class="allocation-current-price-label">Prezzo attuale</div>'
        '<div class="allocation-current-price-row">'
        f'<span class="allocation-current-price-value">{escape(_format_price(current_price, currency))}</span>'
        f'<span class="allocation-current-price-change {daily_class}">{escape(daily_text)}</span>'
        '</div>'
        '</div>'
    )


def _target_marker_left_pct(current_price: float | None, scenarios: list[dict]) -> float | None:
    """Map the current price to the target mini-chart width using scenario values as domain."""
    if current_price is None or current_price <= 0 or not scenarios:
        return None

    values = []
    for item in scenarios:
        value = _safe_float(item.get("value"))
        if value is not None and value > 0:
            values.append(value)
    values.append(float(current_price))

    if len(values) < 2:
        return None

    min_value = min(values)
    max_value = max(values)
    if max_value <= min_value:
        return 50.0

    raw_pct = ((float(current_price) - min_value) / (max_value - min_value)) * 100.0
    return max(6.0, min(94.0, raw_pct))


def _format_signed_eur(value: float | None) -> str:
    if value is None:
        return "€ n/d"
    sign = "+" if value >= 0 else ""
    return sign + fmt_eur(value) + " €"


def _target_item_for_row(row, targets: dict[str, dict]) -> dict | None:
    candidates = (
        row.get("yf_symbol", ""),
        row.get("ticker", ""),
        row.get("display_symbol", ""),
    )
    for candidate in candidates:
        clean = _key(candidate)
        if clean and clean in targets:
            return targets[clean]
    return None


def _fx_to_eur(row, currency: str) -> float | None:
    currency = _key(currency)
    if currency == "EUR":
        return 1.0
    fx = _safe_float(row.get("fx_eur"))
    return fx if fx and fx > 0 else None


def _build_target_scenarios(row, target_item: dict | None) -> list[dict]:
    currency = _key(row.get("valuta"))
    cost_basis = _safe_float(row.get("prezzo_medio"))
    quantity = _safe_float(row.get("quantita"), 0.0) or 0.0
    fx = _fx_to_eur(row, currency)

    scenarios: list[dict] = []
    for field, short_label, label in TARGET_FIELDS:
        if field == "cost_basis":
            value = cost_basis
        else:
            value = _safe_float((target_item or {}).get(field))

        if value is None or value <= 0:
            continue

        pct = ((value - cost_basis) / cost_basis * 100.0) if cost_basis and cost_basis > 0 and field != "cost_basis" else None
        gain_eur = ((value - cost_basis) * quantity * fx) if cost_basis and quantity > 0 and fx and field != "cost_basis" else None

        scenarios.append(
            {
                "field": field,
                "short_label": short_label,
                "label": label,
                "value": value,
                "pct": pct,
                "gain_eur": gain_eur,
                "currency": currency,
                "css_class": value_class(gain_eur or 0.0) if gain_eur is not None else "portfolio-neutral",
            }
        )

    return scenarios


def _render_target_chips(scenarios: list[dict]) -> str:
    if len(scenarios) <= 1:
        return (
            '<div class="allocation-target-empty">'
            'Target non disponibili per questa posizione'
            '</div>'
        )

    chips = []
    for item in scenarios:
        is_current = item["field"] == "cost_basis"
        pct_html = "prezzo" if is_current else _format_signed_pct(item.get("pct"))
        eur_html = "carico" if is_current else _format_signed_eur(item.get("gain_eur"))
        css_class = "allocation-target-neutral" if is_current else (
            "allocation-target-positive" if (item.get("gain_eur") or 0) >= 0 else "allocation-target-negative"
        )
        chips.append(
            '<div class="allocation-target-chip">'
            f'<div class="allocation-target-chip-label">{escape(item["short_label"].upper())}</div>'
            f'<div class="allocation-target-chip-price">{escape(_format_price(item["value"], item["currency"]))}</div>'
            f'<div class="allocation-target-chip-pct {css_class}">{escape(pct_html)}</div>'
            f'<div class="allocation-target-chip-money {css_class}">{escape(eur_html)}</div>'
            '</div>'
        )
    return '<div class="allocation-target-chip-grid">' + "".join(chips) + '</div>'


def _render_target_towers(scenarios: list[dict], current_price: float | None = None, current_currency: str = "") -> str:
    if len(scenarios) <= 1:
        return ""

    max_value = max((_safe_float(item.get("value"), 0.0) or 0.0) for item in scenarios)
    if max_value <= 0:
        return ""

    marker_left = _target_marker_left_pct(current_price, scenarios)
    marker_html = ""
    if marker_left is not None and current_price is not None:
        marker_html = (
            f'<div class="allocation-target-current-marker" style="left:{marker_left:.2f}%">'
            '<div class="allocation-target-current-marker-line"></div>'
            '<div class="allocation-target-current-marker-dot"></div>'
            f'<div class="allocation-target-current-marker-label">Attuale {escape(_format_price(current_price, current_currency))}</div>'
            '</div>'
        )

    bars = []
    for item in scenarios:
        value = _safe_float(item.get("value"), 0.0) or 0.0
        height_pct = max(12.0, min(100.0, value / max_value * 100.0))
        is_current = item["field"] == "cost_basis"
        bar_class = "allocation-target-current-bar" if is_current else "allocation-target-scenario-bar"
        if not is_current and item.get("gain_eur") is not None and item["gain_eur"] < 0:
            bar_class += " allocation-target-negative-bar"
        gain_text = "" if is_current else _format_signed_eur(item.get("gain_eur"))
        bars.append(
            '<div class="allocation-target-tower-item">'
            f'<div class="allocation-target-tower-value">{escape(_format_price(value, item["currency"]))}</div>'
            '<div class="allocation-target-tower-track">'
            f'<div class="allocation-target-tower-bar {bar_class}" style="height:{height_pct:.1f}%"></div>'
            '</div>'
            f'<div class="allocation-target-tower-label">{escape(item["short_label"])}</div>'
            f'<div class="allocation-target-tower-money">{escape(gain_text)}</div>'
            '</div>'
        )

    return (
        '<div class="allocation-target-towers-title">Mini grafico target</div>'
        '<div class="allocation-target-towers">'
        + marker_html
        + "".join(bars)
        + '</div>'
    )


def _render_target_block(row, target_item: dict | None) -> str:
    scenarios = _build_target_scenarios(row, target_item)
    chips_html = _render_target_chips(scenarios)
    current_price = _current_market_price(row)
    towers_html = _render_target_towers(scenarios, current_price, _key(row.get("valuta")))
    return (
        '<div class="allocation-target-block">'
        '<div class="allocation-target-block-title">Target analisti · impatto posizione</div>'
        + chips_html
        + towers_html
        + '<div class="allocation-target-note">€ stimati = (target - prezzo di carico) × quantità × cambio EUR</div>'
        '</div>'
    )


def render_summary_cards(metrics: dict) -> None:
    cols = st.columns(4)

    with cols[0]:
        _summary_card("Valore totale", f"{fmt_eur(metrics.get('total_value', 0.0))} EUR")
    with cols[1]:
        _summary_card("Posizioni", str(metrics.get("positions_count", 0)), "titoli visibili")
    with cols[2]:
        _summary_card("Prima posizione", str(metrics.get("top_title", "-")), fmt_pct(metrics.get("top_weight_pct", 0.0)))
    with cols[3]:
        _summary_card("Concentrazione Top 3", fmt_pct(metrics.get("top3_weight_pct", 0.0)))


def render_position_weight_list(position_allocation) -> None:
    st.markdown('<div class="allocation-section-title">Dettaglio pesi</div>', unsafe_allow_html=True)

    for _, row in position_allocation.iterrows():
        display_symbol = _allocation_display_symbol(row)
        html = (
            '<div class="allocation-weight-row">'
            '<div>'
            f'<div class="allocation-weight-title">{escape(str(row["titolo"]))}</div>'
            f'<div class="allocation-weight-subtitle">{escape(display_symbol)} · {escape(str(row["valuta"]))}</div>'
            '</div>'
            '<div class="allocation-weight-values">'
            f'<div>{escape(fmt_pct(row["weight_pct"]))}</div>'
            f'<div>{escape(fmt_eur(row["value_eur"]))} EUR</div>'
            '</div>'
            '</div>'
        )
        st.markdown(html, unsafe_allow_html=True)


def render_concentration_heatmap(position_allocation) -> None:
    st.markdown('<div class="allocation-section-title">Mappa concentrazione</div>', unsafe_allow_html=True)

    targets = load_user_targets_map()
    cols_per_row = 3
    for start in range(0, len(position_allocation), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, (_, row) in zip(cols, position_allocation.iloc[start:start + cols_per_row].iterrows()):
            css_class = concentration_class(row["weight_pct"])
            label = concentration_label(row["weight_pct"])
            display_symbol = _allocation_display_symbol(row)
            target_item = _target_item_for_row(row, targets)
            current_price_html = _render_current_price_box(row)
            target_html = _render_target_block(row, target_item)
            html = (
                f'<div class="allocation-heat-card allocation-heat-card-targets {css_class}">'
                '<div class="allocation-heat-header">'
                '<div>'
                f'<div class="allocation-heat-title">{escape(str(row["titolo"]))}</div>'
                f'<div class="allocation-heat-label">{escape(display_symbol)} · {escape(str(row["valuta"]))}</div>'
                '</div>'
                '<div class="allocation-heat-values">'
                f'<div class="allocation-heat-weight">{escape(fmt_pct(row["weight_pct"]))}</div>'
                f'<div class="allocation-heat-value-eur">{escape(fmt_eur(row["value_eur"]))} €</div>'
                '</div>'
                '</div>'                f'{current_price_html}'

                f'<div class="allocation-heat-label allocation-heat-risk-label">{escape(label)}</div>'
                + target_html
                + '</div>'
            )
            with col:
                st.markdown(html, unsafe_allow_html=True)


def render_insights(insights: list[str]) -> None:
    items = "".join(f"<li>{escape(str(item))}</li>" for item in insights)
    html = (
        '<div class="allocation-insights-box">'
        '<div class="allocation-insights-title">🧠 Insight allocazione</div>'
        f'<ul>{items}</ul>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_desktop_allocation_dashboard(position_allocation, currency_allocation, market_allocation, metrics, insights) -> None:
    render_summary_cards(metrics)

    left, right = st.columns([1.25, 1.0])

    with left:
        total_label = f"Totale<br>{fmt_eur(metrics.get('total_value', 0.0))} EUR"
        st.plotly_chart(create_position_donut(position_allocation, total_label), use_container_width=True)

    with right:
        render_position_weight_list(position_allocation)

    st.plotly_chart(create_position_bar(position_allocation), use_container_width=True)

    render_concentration_heatmap(position_allocation)


def render_mobile_allocation_dashboard(position_allocation, currency_allocation, market_allocation, metrics, insights) -> None:
    """Compact mobile view.

    Mobile keeps the most useful position-level allocation chart and removes
    currency/market bar charts and insights to reduce vertical clutter.
    """
    render_summary_cards(metrics)
    render_position_weight_list(position_allocation)
    st.plotly_chart(create_position_bar(position_allocation, mobile=True), use_container_width=True, config={"displayModeBar": False})
    render_concentration_heatmap(position_allocation)
