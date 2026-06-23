import html

import streamlit as st

from utils.portfolio_formatting import fmt_eur, fmt_num, fmt_pct, fmt_qty, value_class
from utils.portfolio_tradingview import build_tradingview_symbol


# Colonne: Titolo, Valuta, Quantità, Prezzo medio, Prezzo mercato,
# Var quotidiana, Valore mercato, Guadagno, Target, Azioni.
# Target mostra Min/Med/Max calcolati dal prezzo medio di carico.
COLUMN_WEIGHTS = [2.05, 0.65, 0.75, 1.05, 1.00, 1.12, 1.15, 1.12, 2.65, 2.25]


def _esc(value) -> str:
    """Escape text values before injecting them into small HTML snippets."""
    return html.escape(str(value or ""), quote=True)


def _money_with_currency(value: float, currency: str) -> str:
    """Format a money amount and append the row currency."""
    clean_currency = str(currency or "").strip().upper()
    suffix = f" {clean_currency}" if clean_currency else ""
    return f"{fmt_eur(value)}{suffix}"




def _fx_label(row, currency: str) -> str:
    """Return a read-only FX label for non-EUR rows.

    FX 1.0000 on a non-EUR position is highlighted because it usually means
    the row is using the technical fallback instead of a real conversion rate.
    """
    clean_currency = str(currency or "").strip().upper()
    if clean_currency == "EUR":
        return ""

    try:
        fx_value = float(row.get("fx_eur", 1.0) or 1.0)
    except (TypeError, ValueError):
        return " · FX n/d ⚠️"

    label = f" · FX {fmt_num(fx_value, 4)}"
    if fx_value == 1.0:
        label += " ⚠️"
    return label


def render_portfolio_summary(totals: dict) -> None:
    html_summary = (
        '<div class="portfolio-summary-wrapper">'
        '<div class="portfolio-summary-card">'
        '<div class="portfolio-summary-label">Valorizzazione EUR</div>'
        f'<div class="portfolio-summary-value">{fmt_eur(totals["valore_mercato"])} EUR</div>'
        '</div>'
        '<div class="portfolio-summary-card">'
        '<div class="portfolio-summary-label">Var quotidiana EUR</div>'
        f'<div class="portfolio-summary-value {value_class(totals["var_quotidiana"])}">{fmt_eur(totals["var_quotidiana"])} EUR</div>'
        '</div>'
        '<div class="portfolio-summary-card">'
        '<div class="portfolio-summary-label">Guadagno EUR</div>'
        f'<div class="portfolio-summary-value {value_class(totals["var_da_carico"])}">'
        f'{fmt_eur(totals["var_da_carico"])} EUR'
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
        "Var oggi<br>% / valuta",
        "Val di mercato €",
        "Guadagno<br>valuta",
        "Target",
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
    valuta_raw = str(row["valuta"] or "").strip().upper()
    valuta = _esc(valuta_raw)

    effective_tv_symbol = build_tradingview_symbol(
        row.get("mercato", ""),
        row.get("ticker", ""),
        row.get("tv_symbol", ""),
        row.get("valuta", ""),
    )
    subtitle = _esc(f"{effective_tv_symbol}{_fx_label(row, valuta_raw)}")

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
            _metric_html(
                daily_class,
                fmt_pct(row["var_quotidiana_pct"]),
                _money_with_currency(row["var_quotidiana_eur"], valuta_raw),
            ),
            unsafe_allow_html=True,
        )

    with cols[6]:
        st.markdown(
            f'<div class="portfolio-cell portfolio-row-cell right">{fmt_eur(row["valore_mercato_eur"])} EUR</div>',
            unsafe_allow_html=True,
        )

    with cols[7]:
        st.markdown(
            _metric_html(
                gain_class,
                _money_with_currency(row["var_da_carico_eur"], valuta_raw),
                fmt_pct(row["var_da_carico_pct"]),
            ),
            unsafe_allow_html=True,
        )

    with cols[8]:
        st.markdown(
            str(row.get("portfolio_target_desktop_html", "")) or '<div class="portfolio-target-cell portfolio-row-cell portfolio-target-empty">—</div>',
            unsafe_allow_html=True,
        )

    return cols[9]


def render_row_separator() -> None:
    st.markdown('<div class="portfolio-row-separator"></div>', unsafe_allow_html=True)
