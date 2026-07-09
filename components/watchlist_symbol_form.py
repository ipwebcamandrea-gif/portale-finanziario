import streamlit as st

from components.ticker_lookup_selector import (
    render_ticker_add_intro,
    render_ticker_lookup_selector,
    reset_ticker_lookup,
)
from utils.watchlist_storage import salva_sessione_su_disco
from utils.symbols import normalize_tradingview_symbol


# =========================
# FORM AGGIUNTA SIMBOLO
# =========================

def _add_candidate_to_watchlist(current: str, candidate: dict | None) -> None:
    if not candidate:
        st.warning("Cerca e seleziona un titolo valido.")
        return

    # Salviamo il simbolo TradingView completo, non solo il ticker/yfinance.
    # Esempi: NYSE:BABA, NASDAQ:MSFT, MIL:1MSFT, MIL:SWDA.
    symbol_to_save = str(candidate.get("tv_symbol") or "").strip().upper()
    if not symbol_to_save:
        symbol_to_save = normalize_tradingview_symbol(candidate.get("yf_symbol") or candidate.get("ticker") or "")
    if not symbol_to_save:
        st.warning("Simbolo TradingView non valido.")
        return

    watchlists = st.session_state["tv_watchlists_data"]["watchlists"]
    existing_normalized = {normalize_tradingview_symbol(item) for item in watchlists[current]}
    if symbol_to_save in watchlists[current] or symbol_to_save in existing_normalized:
        st.warning("Simbolo gia presente nella watchlist.")
        return

    watchlists[current].append(symbol_to_save)

    # Reset input condiviso e stati UI coerenti.
    reset_ticker_lookup("tv_add")
    st.session_state["tv_add_symbol_nonce"] = st.session_state.get("tv_add_symbol_nonce", 0) + 1
    st.session_state["tv_confirm_delete_tab"] = False
    st.session_state["tv_show_rename_panel"] = False

    salva_sessione_su_disco()
    st.cache_data.clear()
    st.success(symbol_to_save + " aggiunto.")
    st.rerun()


def render_add_symbol_form(current):
    """Render the same closed-by-default add panel on Watchlist desktop and mobile."""
    with st.expander("➕ Aggiungi titolo", expanded=False):
        render_ticker_add_intro(
            title="➕ Aggiungi titolo",
            subtitle="Cerca per nome o ticker e scegli lo strumento corretto tra NASDAQ, NYSE e Milano.",
        )

        selected_candidate = render_ticker_lookup_selector(key_prefix="tv_add")

        if st.button("Aggiungi", key="tv_add_symbol_btn", use_container_width=True):
            _add_candidate_to_watchlist(current, selected_candidate)
