from __future__ import annotations

import html

import streamlit as st

from utils.portfolio_formatting import fmt_eur, fmt_num, fmt_pct, fmt_qty, value_class


def _esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _money(value: float, currency: str = "EUR") -> str:
    suffix = f" {str(currency or '').upper()}" if currency else ""
    return f"{fmt_eur(value)}{suffix}"


def render_mobile_portfolio_summary(totals: dict) -> None:
    """Render a compact portfolio summary for mobile view."""
    gain_class = value_class(totals.get("var_da_carico", 0.0))
    daily_class = value_class(totals.get("var_quotidiana", 0.0))

    st.markdown(
        (
            '<div class="portfolio-mobile-summary-grid">'
            '<div class="portfolio-mobile-summary-card">'
            '<div class="portfolio-mobile-summary-label">Valore totale</div>'
            f'<div class="portfolio-mobile-summary-value">{fmt_eur(totals.get("valore_mercato", 0.0))} EUR</div>'
            '</div>'
            '<div class="portfolio-mobile-summary-card">'
            '<div class="portfolio-mobile-summary-label">Var oggi</div>'
            f'<div class="portfolio-mobile-summary-value {daily_class}">{fmt_eur(totals.get("var_quotidiana", 0.0))} EUR</div>'
            '</div>'
            '<div class="portfolio-mobile-summary-card portfolio-mobile-summary-wide">'
            '<div class="portfolio-mobile-summary-label">Guadagno</div>'
            f'<div class="portfolio-mobile-summary-value {gain_class}">{fmt_eur(totals.get("var_da_carico", 0.0))} EUR</div>'
            f'<div class="portfolio-mobile-summary-subtitle {gain_class}">{fmt_pct(totals.get("var_da_carico_pct", 0.0))}</div>'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def _render_mobile_metric(label: str, value: str, css_class: str = "") -> str:
    return (
        '<div class="portfolio-mobile-metric">'
        f'<div class="portfolio-mobile-metric-label">{label}</div>'
        f'<div class="portfolio-mobile-metric-value {css_class}">{value}</div>'
        '</div>'
    )


def render_mobile_portfolio_rows(df, tradingview_url_builder) -> None:
    """Render positions as native mobile cards instead of a compressed desktop table."""
    st.markdown('<div class="portfolio-mobile-list-title">Posizioni</div>', unsafe_allow_html=True)

    for idx, row in df.iterrows():
        title = _esc(row.get("titolo", ""))
        ticker = _esc(row.get("ticker", ""))
        mercato = _esc(row.get("mercato", ""))
        valuta = str(row.get("valuta", "")).strip().upper()
        tv_label = _esc(row.get("tv_symbol", "") or f"{mercato}:{ticker}")

        gain_class = value_class(row.get("var_da_carico_eur", 0.0))
        daily_class = value_class(row.get("var_quotidiana_eur", 0.0))

        html_card_open = (
            '<div class="portfolio-mobile-card">'
            '<div class="portfolio-mobile-card-header">'
            '<div>'
            f'<div class="portfolio-mobile-title">{title}</div>'
            f'<div class="portfolio-mobile-subtitle">{mercato}:{ticker} · {valuta}</div>'
            f'<div class="portfolio-mobile-tv-symbol">{tv_label}</div>'
            '</div>'
            f'<div class="portfolio-mobile-daily {daily_class}">{fmt_pct(row.get("var_quotidiana_pct", 0.0))}</div>'
            '</div>'
            '<div class="portfolio-mobile-metrics-grid">'
            + _render_mobile_metric("Valore mercato", f'{fmt_eur(row.get("valore_mercato_eur", 0.0))} EUR')
            + _render_mobile_metric("Guadagno", f'{fmt_eur(row.get("var_da_carico_eur", 0.0))} EUR · {fmt_pct(row.get("var_da_carico_pct", 0.0))}', gain_class)
            + _render_mobile_metric("Var oggi", f'{fmt_eur(row.get("var_quotidiana_eur", 0.0))} EUR · {fmt_pct(row.get("var_quotidiana_pct", 0.0))}', daily_class)
            + _render_mobile_metric("Quantità", fmt_qty(row.get("quantita", 0.0)))
            + _render_mobile_metric("Prezzo medio", fmt_num(row.get("prezzo_medio", 0.0), 5))
            + _render_mobile_metric("Prezzo mercato", fmt_num(row.get("prezzo_mercato", 0.0), 2))
            + '</div>'
        )
        st.markdown(html_card_open, unsafe_allow_html=True)

        # Streamlit columns normally stack on mobile. CSS in portafoglio_mobile.css
        # forces this specific action block to remain a compact inline row.
        st.markdown('<div class="portfolio-mobile-actions-row">', unsafe_allow_html=True)
        action_cols = st.columns(4, gap="small")

        with action_cols[0]:
            st.link_button(
                "📊",
                tradingview_url_builder(
                    row.get("mercato", ""),
                    row.get("ticker", ""),
                    row.get("tv_symbol", ""),
                    row.get("valuta", ""),
                ),
                use_container_width=False,
                help="Apri TradingView esterno",
            )
        with action_cols[1]:
            if st.button("🧮", key=f"portfolio_mobile_sim_{idx}", help="Simula acquisto aggiuntivo", use_container_width=False):
                st.session_state["portfolio_simulation_index"] = idx
                st.session_state["portfolio_edit_index"] = None
                st.session_state["portfolio_delete_index"] = None
                st.rerun()
        with action_cols[2]:
            if st.button("✏️", key=f"portfolio_mobile_edit_{idx}", help="Modifica posizione", use_container_width=False):
                st.session_state["portfolio_edit_index"] = idx
                st.session_state["portfolio_delete_index"] = None
                st.session_state["portfolio_simulation_index"] = None
                st.rerun()
        with action_cols[3]:
            if st.button("🗑️", key=f"portfolio_mobile_delete_{idx}", help="Elimina posizione", use_container_width=False):
                st.session_state["portfolio_delete_index"] = idx
                st.session_state["portfolio_edit_index"] = None
                st.session_state["portfolio_simulation_index"] = None
                st.rerun()

        st.markdown('</div></div>', unsafe_allow_html=True)
