import re

import streamlit as st

from utils.ticker_lookup import format_candidate_label, search_ticker_candidates
from utils.watchlist_storage import salva_sessione_su_disco


def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "")).strip("_") or "empty"


def _render_candidate_details(candidate: dict | None) -> None:
    if candidate:
        st.caption(
            "Scelta: "
            f"{candidate.get('yf_symbol', '-')} · {candidate.get('name', '-')} · "
            f"{candidate.get('market', '-')} · {candidate.get('currency', '-')} · "
            f"TradingView {candidate.get('tv_symbol', '-')}"
        )


def _add_candidate_to_watchlist(current: str, candidate: dict | None) -> None:
    if not candidate:
        st.warning("Cerca e seleziona un titolo valido.")
        return
    symbol_to_save = str(candidate.get("yf_symbol") or "").strip().upper()
    if not symbol_to_save:
        st.warning("Simbolo yfinance non valido.")
        return
    watchlists = st.session_state["tv_watchlists_data"]["watchlists"]
    if symbol_to_save in watchlists[current]:
        st.warning("Simbolo gia presente nella watchlist.")
        return
    watchlists[current].append(symbol_to_save)
    st.session_state["tv_add_symbol_nonce"] = st.session_state.get("tv_add_symbol_nonce", 0) + 1
    st.session_state["tv_confirm_delete_tab"] = False
    st.session_state["tv_show_rename_panel"] = False
    salva_sessione_su_disco()
    st.cache_data.clear()
    st.success(symbol_to_save + " aggiunto.")
    st.rerun()


def render_add_symbol_form(current):
    """Render add-title form for both desktop and compact/mobile Watchlist views."""
    compact_mode = bool(st.session_state.get("tv_compact_rows", False))
    add_input_key = "tv_add_symbol_input_" + str(st.session_state.get("tv_add_symbol_nonce", 0))

    if compact_mode:
        st.markdown(
            "<div class='tv-add-panel'><div class='tv-add-title'>➕ Aggiungi titolo</div>"
            "<div class='tv-add-subtitle'>Cerca per nome o ticker e scegli lo strumento corretto tra NASDAQ, NYSE e Milano.</div></div>",
            unsafe_allow_html=True,
        )
        raw_query = st.text_input("Cerca titolo o ticker", placeholder="Es. AMAZON, AMZN, MICROSOFT, 1AMZN.MI", key=add_input_key)
        query = str(raw_query or "").strip()
        candidates = search_ticker_candidates(query) if query else []
        selected_candidate = None
        if query and not candidates:
            st.warning("Nessun risultato trovato. Prova con il ticker esatto, es. AMZN o 1AMZN.MI.")
        if candidates:
            selected_index = st.selectbox(
                "Titolo / mercato",
                options=list(range(len(candidates))),
                format_func=lambda idx: format_candidate_label(candidates[idx]),
                key="tv_add_candidate_select_" + _safe_key(query),
                help="La lista mostra simbolo yfinance, nome, mercato e valuta.",
            )
            selected_candidate = candidates[selected_index]
            _render_candidate_details(selected_candidate)
        if st.button("Aggiungi", key="tv_add_symbol_btn", use_container_width=True):
            _add_candidate_to_watchlist(current, selected_candidate)
        return

    col_query, col_candidate, col_add = st.columns([2.2, 3.6, 1.0], vertical_alignment="bottom")
    with col_query:
        raw_query = st.text_input("Aggiungi titolo", placeholder="Es. AMAZON, AMZN, MICROSOFT, 1AMZN.MI", label_visibility="collapsed", key=add_input_key)
    query = str(raw_query or "").strip()
    candidates = search_ticker_candidates(query) if query else []
    selected_candidate = None
    with col_candidate:
        if query and not candidates:
            st.warning("Nessun risultato trovato. Prova con il ticker esatto.")
        elif candidates:
            selected_index = st.selectbox(
                "Titolo / mercato",
                options=list(range(len(candidates))),
                format_func=lambda idx: format_candidate_label(candidates[idx]),
                key="tv_add_candidate_select_" + _safe_key(query),
                label_visibility="collapsed",
                help="La lista mostra simbolo yfinance, nome, mercato e valuta.",
            )
            selected_candidate = candidates[selected_index]
            _render_candidate_details(selected_candidate)
        else:
            st.caption("Scrivi un nome o ticker per vedere le alternative NASDAQ, NYSE e Milano.")
    with col_add:
        if st.button("Aggiungi", key="tv_add_symbol_btn", use_container_width=True):
            _add_candidate_to_watchlist(current, selected_candidate)
