from __future__ import annotations

import streamlit as st

from utils.allocazione.allocation_charts import create_group_bar, create_position_bar, create_position_donut
from utils.allocazione.portfolio_allocation import concentration_class, concentration_label
from utils.portfolio_formatting import fmt_eur, fmt_pct


def render_topbar() -> bool:
    st.markdown('<div class="allocation-topbar">', unsafe_allow_html=True)
    col_back, col_refresh, col_mobile, _ = st.columns([1.2, 0.85, 1.3, 6.65])

    with col_back:
        if st.button("← Cockpit", key="allocation_back_to_cockpit", use_container_width=True):
            try:
                st.switch_page("pages/dashboard.py")
            except Exception:
                st.switch_page("main.py")

    with col_refresh:
        if st.button("🔄", key="allocation_refresh", help="Ricarica allocazione", use_container_width=True):
            st.rerun()

    with col_mobile:
        mobile_view = st.toggle("Vista mobile", value=False, key="allocation_mobile_view")

    st.markdown('</div>', unsafe_allow_html=True)
    return bool(mobile_view)


def render_page_header() -> None:
    st.markdown('<div class="allocation-page-title">📊 Allocazione Portafoglio</div>', unsafe_allow_html=True)
    st.markdown('<div class="allocation-page-subtitle">Distribuzione attuale per titolo, valuta, mercato e concentrazione. Tutti i titoli sono sempre visibili.</div>', unsafe_allow_html=True)


def _summary_card(label: str, value: str, subtitle: str = "") -> None:
    html = (
        '<div class="allocation-summary-card">'
        f'<div class="allocation-summary-label">{label}</div>'
        f'<div class="allocation-summary-value">{value}</div>'
        f'<div class="allocation-summary-subtitle">{subtitle}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


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
    st.markdown('<div class="allocation-panel-title">Dettaglio pesi</div>', unsafe_allow_html=True)
    for _, row in position_allocation.iterrows():
        html = (
            '<div class="allocation-weight-row">'
            '<div>'
            f'<div class="allocation-weight-title">{row["titolo"]}</div>'
            f'<div class="allocation-weight-subtitle">{row["mercato"]}:{row["ticker"]} · {row["valuta"]}</div>'
            '</div>'
            '<div class="allocation-weight-values">'
            f'<div>{fmt_pct(row["weight_pct"])}</div>'
            f'<div>{fmt_eur(row["value_eur"])} EUR</div>'
            '</div>'
            '</div>'
        )
        st.markdown(html, unsafe_allow_html=True)


def render_concentration_heatmap(position_allocation) -> None:
    st.markdown('<div class="allocation-section-title">Mappa concentrazione</div>', unsafe_allow_html=True)
    cols_per_row = 3
    for start in range(0, len(position_allocation), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, (_, row) in zip(cols, position_allocation.iloc[start:start + cols_per_row].iterrows()):
            css_class = concentration_class(row["weight_pct"])
            label = concentration_label(row["weight_pct"])
            html = (
                f'<div class="allocation-heat-card {css_class}">'
                f'<div class="allocation-heat-title">{row["titolo"]}</div>'
                f'<div class="allocation-heat-weight">{fmt_pct(row["weight_pct"])}</div>'
                f'<div class="allocation-heat-label">{label}</div>'
                '</div>'
            )
            with col:
                st.markdown(html, unsafe_allow_html=True)


def render_insights(insights: list[str]) -> None:
    items = "".join(f"<li>{item}</li>" for item in insights)
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

    col_currency, col_market = st.columns(2)
    with col_currency:
        st.plotly_chart(create_group_bar(currency_allocation, "valuta", "Allocazione per valuta"), use_container_width=True)
    with col_market:
        st.plotly_chart(create_group_bar(market_allocation, "mercato", "Allocazione per mercato"), use_container_width=True)

    render_concentration_heatmap(position_allocation)
    render_insights(insights)


def render_mobile_allocation_dashboard(position_allocation, currency_allocation, market_allocation, metrics, insights) -> None:
    """Compact mobile view.

    Mobile keeps the most useful position-level allocation chart and removes
    currency/market bar charts to reduce vertical clutter.
    """
    render_summary_cards(metrics)
    render_position_weight_list(position_allocation)
    st.plotly_chart(create_position_bar(position_allocation), use_container_width=True)
    render_insights(insights)
