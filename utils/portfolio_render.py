import html

import streamlit as st

from utils.portfolio_formatting import fmt_eur, fmt_num, fmt_pct, fmt_qty, value_class


# Colonne: Titolo, Valuta, Quantità, Prezzo medio, Prezzo mercato,
# Valore mercato, Guadagno, Var quotidiana, Azioni.
COLUMN_WEIGHTS = [2.35, 0.8, 0.9, 1.25, 1.15, 1.35, 1.35, 1.35, 1.75]


def _esc(value) -> str:
    """Escape text values before injecting them into small HTML snippets."""
    return html.escape(str(value or ""), quote=True)


def render_portfolio_summary(totals: dict) -> None:
    html_summary = (
        '<div class="portfolio-summary-wrapper">'
        '<div class="portfolio-summary-card">'
        '<div class="portfolio-summary-label">Valorizzazione EUR</div>'
        f'<div class="portfolio-summary-value">{fmt_eur(totals["valore_mercato"])}</div>'
        '</div>'
        '<div class="portfolio-summary-card">'
        '<div class="portfolio-summary-label">Var quotidiana EUR</div>'
        f'<div class="portfolio-summary-value {value_class(totals["var_quotidiana"])}">{fmt_eur(totals["var_quotidiana"])}</div>'
        '</div>'
        '<div class="portfolio-summary-card">'
        '<div class="portfolio-summary-label">Guadagno</div>'
        f'<div class="portfolio-summary-value {value_class(totals["var_da_carico"])}">'
        f'{fmt_eur(totals["var_da_carico"])}'
        f'<span class="portfolio-summary-pct">{fmt_pct(totals["var_da_carico_pct"])}</span>'
        '</div>'
        '</div>'
        '</div>'
    )

    st.markdown(html_summary, unsafe_allow_html=True)


def render_portfolio_table_header() -> None:
    cols = st.columns(COLUMN_WEIGHTS, gap="small")

    headers = [
        "Titolo",
        "Valuta",
        "Quantità",
        "P.zo medio<br>di carico",
        "P.zo di<br>mercato",
        "Val di mercato €",
        "Guadagno",
        "Var % quotidiana €",
        "Azioni",
    ]

    for col, header in zip(cols, headers):
        with col:
            st.markdown(
                f'<div class="portfolio-table-header">{header}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="portfolio-row-separator portfolio-header-separator"></div>', unsafe_allow_html=True)


def _metric_html(css_class: str, first_line: str, second_line: str) -> str:
    return (
        f'<div class="portfolio-cell right metric {css_class}">'
        f'<div class="portfolio-metric-line">{first_line}</div>'
        f'<div class="portfolio-metric-line">{second_line}</div>'
        '</div>'
    )


def render_position_values(row):
    """Render all non-action values for a portfolio row and return the action column."""
    daily_class = value_class(row["var_quotidiana_eur"])
    gain_class = value_class(row["var_da_carico_eur"])

    ticker = _esc(row["ticker"])
    titolo = _esc(row["titolo"])
    tv_symbol = _esc(row.get("tv_symbol", ""))
    mercato = _esc(row["mercato"])
    valuta = _esc(row["valuta"])

    subtitle = tv_symbol if tv_symbol else f"{mercato}:{ticker}"

    cols = st.columns(COLUMN_WEIGHTS, gap="small")

    with cols[0]:
        st.markdown(
            '<div class="portfolio-title-cell portfolio-row-cell">'
            f'<span class="portfolio-logo">{ticker[:2]}</span>'
            '<span>'
            f'<span class="portfolio-title">{titolo}</span>'
            f'<span class="portfolio-subtitle">{subtitle}</span>'
            '</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    with cols[1]:
        st.markdown(f'<div class="portfolio-cell portfolio-row-cell">{valuta}</div>', unsafe_allow_html=True)

    with cols[2]:
        st.markdown(
            f'<div class="portfolio-cell portfolio-row-cell right">{fmt_qty(row["quantita"])}</div>',
            unsafe_allow_html=True,
        )

    with cols[3]:
        st.markdown(
            f'<div class="portfolio-cell portfolio-row-cell right">{fmt_num(row["prezzo_medio"], 5)}</div>',
            unsafe_allow_html=True,
        )

    with cols[4]:
        st.markdown(
            f'<div class="portfolio-cell portfolio-row-cell right">{fmt_num(row["prezzo_mercato"], 2)}</div>',
            unsafe_allow_html=True,
        )

    with cols[5]:
        st.markdown(
            f'<div class="portfolio-cell portfolio-row-cell right">{fmt_eur(row["valore_mercato_eur"])}</div>',
            unsafe_allow_html=True,
        )

    with cols[6]:
        st.markdown(
            _metric_html(
                gain_class,
                fmt_eur(row["var_da_carico_eur"]),
                fmt_pct(row["var_da_carico_pct"]),
            ),
            unsafe_allow_html=True,
        )

    with cols[7]:
        st.markdown(
            _metric_html(
                daily_class,
                fmt_pct(row["var_quotidiana_pct"]),
                fmt_eur(row["var_quotidiana_eur"]),
            ),
            unsafe_allow_html=True,
        )

    return cols[8]


def render_row_separator() -> None:
    st.markdown('<div class="portfolio-row-separator"></div>', unsafe_allow_html=True)
