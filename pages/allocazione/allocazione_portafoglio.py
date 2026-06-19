from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
from utils.app_branding import apply_mobile_app_branding, get_app_icon

from components.standard_header import render_standard_page_header


from utils.auth import require_login
from utils.portfolio_calculations import enrich_portfolio_df
from utils.portfolio_prices import refresh_portfolio_quotes
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
    page_icon=get_app_icon(),
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_mobile_app_branding()


def load_css() -> None:
    for css_path in (GLOBAL_CSS_PATH, CSS_PATH):
        if css_path.exists():
            st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def current_allocation_refresh_timestamp() -> str:
    """Return current refresh timestamp in Europe/Rome time."""
    return datetime.now(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y %H:%M:%S")


def render_allocation_refresh_details(result: dict) -> None:
    """Show details about quote refresh failures, if any."""
    failed = result.get("failed", []) or []
    if not failed:
        return

    with st.expander("Dettaglio quotazioni non aggiornate", expanded=False):
        st.write(
            "Questi simboli non sono stati aggiornati da yfinance e quindi mantengono "
            "i valori già presenti nel JSON:"
        )
        for item in failed:
            st.write(f"- {item}")


def refresh_allocation_quotes() -> dict:
    """Force fresh portfolio quotes before rendering allocation values."""
    st.cache_data.clear()
    with st.spinner("Aggiornamento automatico quotazioni in corso..."):
        result = refresh_portfolio_quotes(DATA_PATH)
    st.session_state["allocation_last_refresh_result"] = result
    st.session_state["allocation_last_refresh_timestamp"] = current_allocation_refresh_timestamp()
    return result


def refresh_allocation_quotes_action() -> None:
    refresh_allocation_quotes()
    st.rerun()


def render_allocation_refresh_status(result: dict) -> None:
    updated = result.get("updated", 0)
    total = result.get("total", 0)
    refresh_time = st.session_state.get("allocation_last_refresh_timestamp", "")
    refresh_suffix = f" · Aggiornamento dati: {refresh_time}" if refresh_time else ""

    if updated > 0:
        st.caption(f"Quotazioni aggiornate automaticamente/all'ultimo refresh: {updated} su {total}{refresh_suffix}.")
    else:
        st.caption(f"Aggiornamento eseguito: nessuna quotazione aggiornata, valori manuali mantenuti{refresh_suffix}.")

    render_allocation_refresh_details(result)


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
        refresh_callback=refresh_allocation_quotes_action,
    )

    refresh_result = refresh_allocation_quotes()
    render_allocation_refresh_status(refresh_result)

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
