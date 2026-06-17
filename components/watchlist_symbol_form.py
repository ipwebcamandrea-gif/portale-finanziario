import streamlit as st

from utils.portfolio_market_suggest import MARKET_OPTIONS, suggest_market_for_ticker
from utils.watchlist_storage import salva_sessione_su_disco


# =========================
# FORM AGGIUNTA SIMBOLO
# =========================

def _clean_watchlist_ticker(value: str) -> str:
    return str(value or "").strip().upper().replace(" ", "")


def _symbol_for_selected_market(ticker: str, market: str) -> str:
    """Build the yfinance symbol saved in the watchlist from ticker + selected market.

    The Watchlist data pipeline reads yfinance symbols. For USA markets we keep
    the plain ticker, while for Borsa Italiana we add the .MI suffix when the
    user has not already written it.
    """
    clean_market = str(market or "").strip().upper()
    clean_symbol = _clean_watchlist_ticker(ticker)

    if ":" in clean_symbol:
        clean_symbol = clean_symbol.split(":", 1)[1].strip().upper()

    if clean_market == "MIL":
        if clean_symbol.endswith(".MI"):
            return clean_symbol
        return clean_symbol + ".MI"

    if clean_symbol.endswith(".MI"):
        return clean_symbol[:-3]

    return clean_symbol


def render_add_symbol_form(current):
    # In vista compatta la pagina e solo consultiva:
    # niente input aggiunta titoli e niente pulsante Aggiungi.
    if bool(st.session_state.get("tv_compact_rows", False)):
        return

    # Chiave dinamica per reset automatico input dopo aggiunta.
    add_input_key = "tv_add_symbol_input_" + str(st.session_state.get("tv_add_symbol_nonce", 0))

    col_ticker, col_market, col_add = st.columns([4.2, 1.6, 1.1], vertical_alignment="bottom")

    with col_ticker:
        raw_symbol = st.text_input(
            "Aggiungi simbolo",
            placeholder="Es. AAPL, MSFT, TSLA, SWDA.MI",
            label_visibility="collapsed",
            key=add_input_key,
        )

    new_symbol = _clean_watchlist_ticker(raw_symbol)
    market_suggestion = suggest_market_for_ticker(new_symbol)
    suggested_market = str(market_suggestion.get("market") or "NASDAQ").upper()
    if suggested_market not in MARKET_OPTIONS:
        suggested_market = "NASDAQ"

    last_ticker_key = "tv_add_last_ticker_for_market"
    market_key = "tv_add_market_select"
    if st.session_state.get(last_ticker_key) != new_symbol:
        st.session_state[last_ticker_key] = new_symbol
        st.session_state[market_key] = suggested_market

    current_market = str(st.session_state.get(market_key, suggested_market) or suggested_market).upper()
    if current_market not in MARKET_OPTIONS:
        current_market = suggested_market

    with col_market:
        selected_market = st.selectbox(
            "Mercato",
            MARKET_OPTIONS,
            index=MARKET_OPTIONS.index(current_market),
            key=market_key,
            help="Mercato suggerito automaticamente. Puoi modificarlo manualmente prima di aggiungere il titolo.",
        )

    symbol_to_save = _symbol_for_selected_market(new_symbol, selected_market) if new_symbol else ""
    suggestion_message = market_suggestion.get("message", "")
    if suggestion_message:
        st.caption(f"{suggestion_message} · Selezionato: {selected_market} · Simbolo salvato: {symbol_to_save or '-'}")
    else:
        st.caption(f"Mercato selezionato: {selected_market} · Simbolo salvato: {symbol_to_save or '-'}")

    with col_add:
        if st.button("Aggiungi", key="tv_add_symbol_btn", use_container_width=True):
            if not symbol_to_save:
                st.warning("Inserisci un simbolo valido.")
                return

            watchlists = st.session_state["tv_watchlists_data"]["watchlists"]

            if symbol_to_save in watchlists[current]:
                st.warning("Simbolo gia presente nella watchlist.")
                return

            watchlists[current].append(symbol_to_save)

            # Reset input tramite nonce.
            st.session_state["tv_add_symbol_nonce"] = st.session_state.get("tv_add_symbol_nonce", 0) + 1

            # Reset stati UI coerenti.
            st.session_state["tv_confirm_delete_tab"] = False
            st.session_state["tv_show_rename_panel"] = False

            salva_sessione_su_disco()
            st.cache_data.clear()

            st.success(symbol_to_save + " aggiunto.")
            st.rerun()
