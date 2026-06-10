import streamlit as st
from utils.watchlist_storage import salva_sessione_su_disco


def render_add_symbol_form(current):
    # chiave dinamica per reset automatico input
    add_input_key = "tv_add_symbol_input_" + str(st.session_state.get("tv_add_symbol_nonce", 0))

    col1, col2 = st.columns([5, 1])

    with col1:
        new_symbol = st.text_input(
            "Aggiungi simbolo",
            placeholder="Es. AAPL, MSFT, TSLA, SWDA.MI",
            label_visibility="collapsed",
            key=add_input_key,
        ).upper().strip()

    with col2:
        if st.button("Aggiungi", key="tv_add_symbol_btn", use_container_width=True):

            if not new_symbol:
                st.warning("Inserisci un simbolo valido.")
                return

            watchlists = st.session_state["tv_watchlists_data"]["watchlists"]

            if new_symbol in watchlists[current]:
                st.warning("Simbolo gia presente nella watchlist.")
                return

            # aggiunta simbolo
            watchlists[current].append(new_symbol)

            # reset input tramite nonce
            st.session_state["tv_add_symbol_nonce"] = st.session_state.get("tv_add_symbol_nonce", 0) + 1

            # reset stati UI coerenti
            st.session_state["tv_confirm_delete_tab"] = False
            st.session_state["tv_show_rename_panel"] = False

            # persistenza
            salva_sessione_su_disco()
            st.cache_data.clear()

            st.success(new_symbol + " aggiunto.")
            st.rerun()
