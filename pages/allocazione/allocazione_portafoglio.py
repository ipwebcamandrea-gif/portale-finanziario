
from pathlib import Path

import streamlit as st

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
    render_page_header,
    render_topbar,
)


require_login()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / "portfolio" / "portafoglio.json"
CSS_PATH = BASE_DIR / "css" / "allocazione" / "allocazione_portafoglio.css"


st.set_page_config(
    page_title="Allocazione Portafoglio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_css() -> None:
    if CSS_PATH.exists():
        st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def main() -> None:
    load_css()
    mobile_view = render_topbar()
    render_page_header()

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
