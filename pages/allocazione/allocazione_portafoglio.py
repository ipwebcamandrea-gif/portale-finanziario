from pathlib import Path

import streamlit as st

from components.standard_header import render_standard_page_header


from utils.auth import require_login
from utils.portfolio_calculations import enrich_portfolio_df
from utils.portfolio_storage import load_portfolio
from utils.allocazione.portfolio_allocation import (
    build_allocation_insights,
    calculate_concentration_metrics,
    calculate_group_allocation,
    calculate_position_allocation,
)
from utils.allocazione.allocation_render import (
    render_desktop_allocation_dashboard,
    render_mobile_allocation_dashboard,
)


require_login()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / "portfolio" / "portafoglio.json"
GLOBAL_CSS_PATH = BASE_DIR / "css" / "global.css"
CSS_PATH = BASE_DIR / "css" / "allocazione" / "allocazione_portafoglio.css"


st.set_page_config(
    page_title="Allocazione Portafoglio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_css() -> None:
    for css_path in (GLOBAL_CSS_PATH, CSS_PATH):
        if css_path.exists():
            st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def main() -> None:
    load_css()
    mobile_view = render_standard_page_header(
        title="📊 Allocazione Portafoglio",
        subtitle="Distribuzione attuale per titolo, valuta, mercato e concentrazione. Tutti i titoli sono sempre visibili.",
        toggle_label="📱 Vista mobile",
        toggle_key="allocation_mobile_view",
        toggle_default=True,
        refresh_key="allocation_header_refresh",
        back_key="allocation_header_back",
    )

    df = load_portfolio(DATA_PATH)
    df = enrich_portfolio_df(df)

    if df.empty:
        st.info("Il portafoglio è vuoto. Aggiungi posizioni nella pagina Portafoglio.")
        return

    fx_errors = df.attrs.get("fx_errors", {})
    if fx_errors:
        for currency, error in fx_errors.items():
            st.warning(f"Cambio {currency}/EUR non disponibile da yfinance: {error}")

    position_allocation = calculate_position_allocation(df)
    currency_allocation = calculate_group_allocation(df, "valuta")
    market_allocation = calculate_group_allocation(df, "mercato")
    metrics = calculate_concentration_metrics(position_allocation)
    insights = build_allocation_insights(position_allocation, currency_allocation, market_allocation, metrics)

    if mobile_view:
        render_mobile_allocation_dashboard(position_allocation, currency_allocation, market_allocation, metrics, insights)
    else:
        render_desktop_allocation_dashboard(position_allocation, currency_allocation, market_allocation, metrics, insights)


if __name__ == "__main__":
    main()
