from __future__ import annotations

import re

import streamlit as st

from utils.ticker_lookup import format_candidate_label, search_ticker_candidates


# =========================
# SHARED TICKER LOOKUP SELECTOR
# =========================

def _safe_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "")).strip("_") or "empty"


def render_ticker_add_intro(*, title: str, subtitle: str) -> None:
    """Render the shared add-panel intro card used by Watchlist and Portafoglio."""
    st.markdown(
        "<div class='ticker-add-panel'>"
        f"<div class='ticker-add-title'>{title}</div>"
        f"<div class='ticker-add-subtitle'>{subtitle}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_ticker_lookup_selector(
    *,
    key_prefix: str,
    placeholder: str = "Es. AMAZON, AMZN, MICROSOFT, 1AMZN.MI",
    empty_hint: str = "Scrivi un nome o ticker per vedere le alternative NASDAQ, NYSE e Milano.",
) -> dict | None:
    """Render a vertical, mobile-friendly ticker lookup selector.

    The function returns the selected candidate dict produced by
    utils/ticker_lookup.py, or None when the user has not selected a valid item.
    The same layout is intentionally used on desktop and mobile.
    """
    nonce_key = f"{key_prefix}_ticker_lookup_nonce"
    input_key = f"{key_prefix}_ticker_lookup_input_" + str(st.session_state.get(nonce_key, 0))

    raw_query = st.text_input(
        "Cerca titolo o ticker",
        placeholder=placeholder,
        key=input_key,
    )
    query = str(raw_query or "").strip()
    candidates = search_ticker_candidates(query) if query else []
    selected_candidate = None

    if query and not candidates:
        st.warning("Nessun risultato trovato. Prova con il ticker esatto, es. AMZN o 1AMZN.MI.")
    elif candidates:
        selected_index = st.selectbox(
            "Titolo / mercato",
            options=list(range(len(candidates))),
            format_func=lambda idx: format_candidate_label(candidates[idx]),
            key=f"{key_prefix}_ticker_lookup_candidate_" + _safe_key(query),
            help="La lista mostra simbolo yfinance, nome, mercato e valuta.",
        )
        selected_candidate = candidates[selected_index]
        st.caption(
            "Scelta: "
            f"{selected_candidate.get('yf_symbol', '-')} · "
            f"{selected_candidate.get('name', '-')} · "
            f"{selected_candidate.get('market', '-')} · "
            f"{selected_candidate.get('currency', '-')} · "
            f"TradingView {selected_candidate.get('tv_symbol', '-')}"
        )
    else:
        st.caption(empty_hint)

    return selected_candidate


def reset_ticker_lookup(key_prefix: str) -> None:
    """Reset the shared input on the next rerun."""
    nonce_key = f"{key_prefix}_ticker_lookup_nonce"
    st.session_state[nonce_key] = st.session_state.get(nonce_key, 0) + 1
