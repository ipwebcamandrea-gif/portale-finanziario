from html import escape
import streamlit as st


def render_header():
    st.markdown(
        """
        <div class="tv-page-header">
            <div class="tv-page-title">Watchlist TradingView</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_persistence_note():
    storage_mode = st.session_state.get("tv_storage_mode", "locale")
    last_error = st.session_state.get("tv_last_github_error", "")

    if storage_mode == "github":
        title = "Modalita GitHub API"
        text = "Le modifiche vengono salvate su watchlists.json su GitHub."
    elif storage_mode == "locale_fallback":
        title = "Modalita locale fallback"
        text = "GitHub non disponibile. Ultimo errore: " + last_error
    else:
        title = "Modalita JSON locale"
        text = "Salvataggio locale attivo."

    st.markdown(
        f"""
        <div class="tv-persistence-note">
            <div class="tv-persistence-title">{escape(title)}</div>
            <div class="tv-persistence-text">{escape(text)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_watchlist_header():
    col1, col2 = st.columns([5.0, 1.35], vertical_alignment="center")

    with col1:
        render_header()
        render_persistence_note()

    with col2:
        st.markdown('<div class="tv-modern-back-button">', unsafe_allow_html=True)
        if st.button("← Cockpit", key="tv_back_cockpit", use_container_width=True):
            st.switch_page("pages/dashboard.py")
        st.markdown('</div>', unsafe_allow_html=True)
