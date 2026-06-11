from html import escape

import streamlit as st


# =========================
# RENDER HEADER
# =========================

def render_header():
    st.markdown(
        """
        <div class="tv-page-header">
            <div class="tv-page-title">Watchlist TradingView</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


# =========================
# CONTROLLI COMPATTI / REFRESH
# =========================

def render_compact_refresh_controls():
    """
    Controlli globali della pagina watchlist.
    Sono posizionati sotto il pulsante Cockpit:
    - toggle vista compatta
    - refresh dati solo icona
    """
    if "tv_compact_rows" not in st.session_state:
        st.session_state["tv_compact_rows"] = False

    st.toggle(
        "📱 Vista compatta",
        key="tv_compact_rows",
        help="Mostra righe compatte ottimizzate per smartphone. In questa vista il tap sulla riga apre TradingView.",
    )

    if st.button(
        "🔄",
        key="tv_refresh_data",
        use_container_width=True,
        help="Aggiorna dati",
    ):
        st.cache_data.clear()
        st.rerun()


# =========================
# ENTRY POINT HEADER
# =========================

def render_watchlist_header():
    header_col_1, header_col_2 = st.columns([5.0, 1.35], vertical_alignment="center")

    with header_col_1:
        render_header()
        render_persistence_note()

    with header_col_2:
        st.markdown('<div class="tv-modern-back-button">', unsafe_allow_html=True)
        if st.button("← Cockpit", key="tv_back_cockpit", use_container_width=True):
            st.switch_page("pages/dashboard.py")
        st.markdown("</div>", unsafe_allow_html=True)

        render_compact_refresh_controls()
