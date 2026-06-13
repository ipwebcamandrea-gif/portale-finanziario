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
            <div class="tv-page-subtitle">Watchlist operativa con tab, SMA 200W, viste compatte e apertura grafici TradingView.</div>
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
# CONTROLLI HEADER WATCHLIST
# =========================

def render_header_controls():
    """Header controls local to Watchlist TradingView.

    This is intentionally private/safe for this page: Watchlist TradingView keeps
    its own compact toggle, refresh and cockpit buttons so they never disappear.
    """
    if "tv_compact_rows" not in st.session_state:
        st.session_state["tv_compact_rows"] = True

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
        if st.button("← Cockpit", key="tv_back_cockpit", use_container_width=True):
            st.switch_page("pages/dashboard.py")


# =========================
# ENTRY POINT HEADER
# =========================

def render_watchlist_header():
    if "tv_compact_rows" not in st.session_state:
        st.session_state["tv_compact_rows"] = True

    compact_mode = bool(st.session_state.get("tv_compact_rows", True))

    header_col_1, header_col_2 = st.columns(
        [3.55, 2.45],
        vertical_alignment="center",
    )

    with header_col_1:
        render_header()

    with header_col_2:
        render_header_controls()

    if not compact_mode:
        render_persistence_note()
