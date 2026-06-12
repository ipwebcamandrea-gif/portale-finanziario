import textwrap

import streamlit as st

from utils.portfolio_formatting import fmt_eur, fmt_num, fmt_pct, fmt_qty, value_class


COLUMN_WEIGHTS = [2.2, 1.0, 0.8, 0.9, 1.2, 1.1, 1.3, 1.3, 1.3, 1.2]


def _html(markup: str) -> str:
    """Return left-aligned HTML so Streamlit Markdown does not render it as a code block."""
    return textwrap.dedent(markup).strip()


def render_portfolio_summary(totals: dict) -> None:
    st.markdown(
        _html(
            f"""
            <div class="portfolio-summary-wrapper">
                <div class="portfolio-summary-card">
                    <div class="portfolio-summary-label">Valorizzazione EUR</div>
                    <div class="portfolio-summary-value">
                        {fmt_eur(totals["valore_mercato"])}
                    </div>
                </div>
                <div class="portfolio-summary-card">
                    <div class="portfolio-summary-label">Var quotidiana EUR</div>
                    <div class="portfolio-summary-value {value_class(totals["var_quotidiana"])}">
                        {fmt_eur(totals["var_quotidiana"])}
                    </div>
                </div>
                <div class="portfolio-summary-card">
                    <div class="portfolio-summary-label">Var da carico</div>
                    <div class="portfolio-summary-value {value_class(totals["var_da_carico"])}">
                        {fmt_eur(totals["var_da_carico"])}
                        <span class="portfolio-summary-pct">
                            {fmt_pct(totals["var_da_carico_pct"])}
                        </span>
                    </div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_portfolio_table_header() -> None:
    cols = st.columns(COLUMN_WEIGHTS)

    headers = [
        "Titolo",
        "Strumento",
        "Valuta",
        "Quantità",
        "P.zo medio<br>di carico",
        "P.zo di<br>mercato",
        "Val di mercato €",
        "Var % quotidiana €",
        "Var % da carico €",
        "Azioni",
    ]

    for col, header in zip(cols, headers):
        with col:
            st.markdown(
                f'<div class="portfolio-table-header">{header}</div>',
                unsafe_allow_html=True,
            )


def render_position_values(row):
    """Render all non-action values for a portfolio row and return the action column."""
    daily_class = value_class(row["var_quotidiana_eur"])
    load_class = value_class(row["var_da_carico_eur"])

    cols = st.columns(COLUMN_WEIGHTS)

    with cols[0]:
        st.markdown(
            _html(
                f"""
                <div class="portfolio-title-cell">
                    <span class="portfolio-logo">{str(row["ticker"])[:2]}</span>
                    <span>
                        <span class="portfolio-title">{row["titolo"]}</span>
                        <span class="portfolio-subtitle">{row["mercato"]}:{row["ticker"]}</span>
                    </span>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with cols[1]:
        st.markdown(
            f'<div class="portfolio-cell">{row["strumento"]}</div>',
            unsafe_allow_html=True,
        )

    with cols[2]:
        st.markdown(
            f'<div class="portfolio-cell">{row["valuta"]}</div>',
            unsafe_allow_html=True,
        )

    with cols[3]:
        st.markdown(
            f'<div class="portfolio-cell right">{fmt_qty(row["quantita"])}</div>',
            unsafe_allow_html=True,
        )

    with cols[4]:
        st.markdown(
            f'<div class="portfolio-cell right">{fmt_num(row["prezzo_medio"], 5)}</div>',
            unsafe_allow_html=True,
        )

    with cols[5]:
        st.markdown(
            f'<div class="portfolio-cell right">{fmt_num(row["prezzo_mercato"], 2)}</div>',
            unsafe_allow_html=True,
        )

    with cols[6]:
        st.markdown(
            f'<div class="portfolio-cell right">{fmt_eur(row["valore_mercato_eur"])}</div>',
            unsafe_allow_html=True,
        )

    with cols[7]:
        st.markdown(
            _html(
                f"""
                <div class="portfolio-cell right metric {daily_class}">
                    <span>{fmt_pct(row["var_quotidiana_pct"])}</span>
                    <span>{fmt_eur(row["var_quotidiana_eur"])}</span>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with cols[8]:
        st.markdown(
            _html(
                f"""
                <div class="portfolio-cell right metric {load_class}">
                    <span>{fmt_pct(row["var_da_carico_pct"])}</span>
                    <span>{fmt_eur(row["var_da_carico_eur"])}</span>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    return cols[9]
