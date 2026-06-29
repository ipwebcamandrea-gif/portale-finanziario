from __future__ import annotations

import html
from urllib.parse import parse_qs, unquote, urlparse

import streamlit as st

from utils.portfolio_formatting import fmt_eur, fmt_num, fmt_pct, fmt_qty, value_class


def _esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _money(value: float, currency: str = "EUR") -> str:
    suffix = f" {str(currency or '').upper()}" if currency else ""
    return f"{fmt_eur(value)}{suffix}"




def _fx_label(row, currency: str) -> str:
    """FX is shown once in the portfolio page, not repeated in every mobile card."""
    return ""


def _target_url_from_tradingview_url(tv_url: str) -> str:
    """Convert a TradingView chart URL into the analyst forecast URL."""
    try:
        parsed = urlparse(tv_url)
        path_parts = [part for part in parsed.path.split("/") if part]

        if "symbols" in path_parts:
            symbols_index = path_parts.index("symbols")
            if symbols_index + 1 < len(path_parts):
                tv_symbol_path = path_parts[symbols_index + 1].strip()
                if tv_symbol_path:
                    return f"https://www.tradingview.com/symbols/{tv_symbol_path}/forecast/"

        query_symbol = parse_qs(parsed.query).get("symbol", [""])[0]
        query_symbol = unquote(query_symbol).strip()
        if query_symbol:
            tv_symbol_path = query_symbol.replace(":", "-")
            return f"https://www.tradingview.com/symbols/{tv_symbol_path}/forecast/"
    except Exception:
        pass

    return tv_url


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


def _render_one_mobile_portfolio_card(row, idx, df, tradingview_url_builder, inline_renderer=None, target_renderer=None) -> None:
    """Render one portfolio card in the mobile/card view only."""
    title = _esc(row.get("titolo", ""))
    valuta = str(row.get("valuta", "")).strip().upper()

    tv_symbol_raw = str(row.get("tv_symbol", "") or "").strip()
    fallback_symbol = f"{row.get('mercato', '')}:{row.get('ticker', '')}"
    display_symbol = _esc(tv_symbol_raw if tv_symbol_raw else fallback_symbol)

    gain_class = value_class(row.get("var_da_carico_eur", 0.0))
    daily_class = value_class(row.get("var_quotidiana_eur", 0.0))

    html_card_open = (
        '<div class="portfolio-mobile-card">'
        '<div class="portfolio-mobile-card-header">'
        '<div>'
        f'<div class="portfolio-mobile-title">{title}</div>'
        f'<div class="portfolio-mobile-subtitle">{display_symbol} · {valuta}{_fx_label(row, valuta)}</div>'
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
        + str(row.get("portfolio_target_mobile_html", "") or "")
    )
    st.markdown(html_card_open, unsafe_allow_html=True)

    tv_url = tradingview_url_builder(
        row.get("mercato", ""),
        row.get("ticker", ""),
        row.get("tv_symbol", ""),
        row.get("valuta", ""),
    )
    target_url = _target_url_from_tradingview_url(tv_url)

    st.markdown('<div class="portfolio-mobile-actions-grid">', unsafe_allow_html=True)
    row_1_col_1, row_1_col_2 = st.columns(2, gap="small")
    with row_1_col_1:
        st.link_button("📊", tv_url, use_container_width=True, help="Apri TradingView esterno")
    with row_1_col_2:
        if st.button("🧮", key=f"portfolio_mobile_sim_{idx}", help="Simula acquisto aggiuntivo", use_container_width=True):
            st.session_state["portfolio_simulation_index"] = idx
            st.session_state["portfolio_edit_index"] = None
            st.session_state["portfolio_delete_index"] = None
            st.rerun()

    row_2_col_1, row_2_col_2 = st.columns(2, gap="small")
    with row_2_col_1:
        if st.button("✏️", key=f"portfolio_mobile_edit_{idx}", help="Modifica posizione", use_container_width=True):
            st.session_state["portfolio_edit_index"] = idx
            st.session_state["portfolio_delete_index"] = None
            st.session_state["portfolio_simulation_index"] = None
            st.rerun()
    with row_2_col_2:
        if st.button("🗑️", key=f"portfolio_mobile_delete_{idx}", help="Elimina posizione", use_container_width=True):
            st.session_state["portfolio_delete_index"] = idx
            st.session_state["portfolio_edit_index"] = None
            st.session_state["portfolio_simulation_index"] = None
            st.rerun()

    row_3_col_1, row_3_col_2 = st.columns(2, gap="small")
    with row_3_col_1:
        with st.container(key=f"portfolio_mobile_target_{idx}"):
            if target_renderer is not None:
                if st.button("🎯", key=f"portfolio_mobile_target_btn_{idx}", use_container_width=True, help="Apri Target Analisti interno"):
                    target_renderer(row)
            else:
                st.link_button("🎯", target_url, use_container_width=True, help="Apri target analisti TradingView")
    with row_3_col_2:
        st.empty()
    st.markdown('</div>', unsafe_allow_html=True)

    if inline_renderer is not None:
        inline_renderer(df, idx)
    st.markdown('</div>', unsafe_allow_html=True)


def render_mobile_portfolio_rows(df, tradingview_url_builder, inline_renderer=None, target_renderer=None) -> None:
    """Render positions as a responsive card grid in the mobile/card view only.

    The desktop table view is intentionally untouched.
    """
    st.markdown('<div class="portfolio-mobile-list-title">Posizioni</div>', unsafe_allow_html=True)

    rows = list(df.iterrows())
    if not rows:
        return

    cards_per_row = 3
    for start in range(0, len(rows), cards_per_row):
        chunk = rows[start:start + cards_per_row]
        columns = st.columns(cards_per_row, gap="medium")
        for column, (idx, row) in zip(columns, chunk):
            with column:
                _render_one_mobile_portfolio_card(
                    row,
                    idx,
                    df,
                    tradingview_url_builder,
                    inline_renderer=inline_renderer,
                    target_renderer=target_renderer,
                )
