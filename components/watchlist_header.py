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
# CONTROLLI HEADER
# =========================

def render_header_controls():
    """
    Controlli globali su una sola riga header:
    - toggle vista compatta
    - refresh dati
    - ritorno Cockpit
    """
    if "tv_compact_rows" not in st.session_state:
        st.session_state["tv_compact_rows"] = False

    compact_col, refresh_col, back_col = st.columns(
        [1.55, 0.42, 1.10],
        vertical_alignment="center",
        gap="small",
    )

    with compact_col:
        st.toggle(
            "📱 Vista compatta",
            key="tv_compact_rows",
            help="Mostra righe compatte ottimizzate per smartphone. In questa vista il tap sulla riga apre TradingView.",
        )

    with refresh_col:
        if st.button(
            "🔄",
            key="tv_refresh_data",
            use_container_width=True,
            help="Aggiorna dati",
        ):
            st.cache_data.clear()
            st.rerun()

    with back_col:
        st.markdown('<div class="tv-modern-back-button">', unsafe_allow_html=True)
        if st.button("← Cockpit", key="tv_back_cockpit", use_container_width=True):
            st.switch_page("pages/dashboard.py")
        st.markdown("</div>", unsafe_allow_html=True)


# =========================
# ENTRY POINT HEADER
# =========================

def render_watchlist_header():
    if "tv_compact_rows" not in st.session_state:
        st.session_state["tv_compact_rows"] = False

    compact_mode = bool(st.session_state.get("tv_compact_rows", False))

    header_col_1, header_col_2 = st.columns(
        [3.55, 2.45],
        vertical_alignment="center",
    )

    with header_col_1:
        render_header()

    with header_col_2:
        render_header_controls()

    # In vista compatta la nota gialla GitHub/fallback viene nascosta
    # per lasciare spazio alla sola consultazione della watchlist.
    if not compact_mode:
        render_persistence_note()
