from html import escape

import streamlit as st

from components.standard_header import render_standard_page_header


# =========================
# PERSISTENCE NOTE
# =========================

def render_persistence_note():
    storage_mode = st.session_state.get("tv_storage_mode", "locale")
    last_error = st.session_state.get("tv_last_github_error", "")

    if storage_mode == "github":
        title = "Modalita GitHub API"
        text = "Le modifiche vengono salvate su watchlists.json nel branch data-watchlists del repository GitHub."
    elif storage_mode == "locale_fallback":
        title = "Modalita locale fallback"
        text = "GitHub API non disponibile: le modifiche vengono salvate localmente. Ultimo errore: " + last_error
    else:
        title = "Modalita JSON locale"
        text = "Le modifiche vengono salvate su watchlists.json nell'ambiente dell'app."

    st.markdown(
        f"""
        <div class="tv-persistence-note">
            <div class="tv-persistence-title">{escape(title)}</div>
            <div class="tv-persistence-text">{escape(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _refresh_watchlist() -> None:
    st.cache_data.clear()
    st.rerun()


# =========================
# ENTRY POINT HEADER
# =========================

def render_watchlist_header():
    compact_mode = render_standard_page_header(
        title="Watchlist TradingView",
        subtitle="Watchlist operativa con tab, SMA 200W, viste compatte e apertura grafici TradingView.",
        toggle_label="📱 Vista compatta",
        toggle_key="tv_compact_rows",
        toggle_default=True,
        refresh_key="tv_refresh_data",
        back_key="tv_back_cockpit",
        refresh_callback=_refresh_watchlist,
    )

    if not compact_mode:
        render_persistence_note()
