import streamlit as st
from pathlib import Path


# =========================
# PROTEZIONE LOGIN
# =========================

if not st.session_state.get("authenticated", False):
    st.error("Accesso non autorizzato.")

    if st.button("Torna al Login"):
        st.switch_page("main.py")

    st.stop()


# =========================
# CONFIGURAZIONE FILE / CSS
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent

GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
DASHBOARD_CSS = ROOT_DIR / "css" / "dashboard.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(
                f"<style>{file.read()}</style>",
                unsafe_allow_html=True
            )


local_css(GLOBAL_CSS)
local_css(DASHBOARD_CSS)


# =========================
# HEADER
# =========================

st.markdown(
    """
    <div class="cockpit-header">
        <div class="cockpit-eyebrow">FinancePortal 2026 · V1.1 Development</div>
        <div class="main-title">Portafoglio Cockpit</div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# MENU PRINCIPALE
# =========================

col_watchlist, col_watchlist_tv, col_portafoglio, col_logout = st.columns(4)

with col_watchlist:
    if st.button(
        "📊  Watchlist\n\nPrezzi, SMA 200W, stato tecnico e grafici.",
        key="card_watchlist",
        use_container_width=True
    ):
        st.switch_page("pages/watchlist.py")

with col_watchlist_tv:
    if st.button(
        "📺  Watchlist TradingView\n\nMulti-tab, SMA 200W, drag & drop e grafici.",
        key="card_watchlist_tradingview",
        use_container_width=True
    ):
        st.switch_page("pages/watchlist_tradingview.py")

with col_portafoglio:
    if st.button(
        "💼  Portafoglio\n\nArea dedicata alle posizioni reali.",
        key="card_portafoglio",
        use_container_width=True
    ):
        st.switch_page("pages/portafoglio.py")

with col_logout:
    if st.button(
        "🚪  Logout\n\nChiudi la sessione e torna al login.",
        key="card_logout",
        use_container_width=True
    ):
        st.switch_page("pages/logout.py")


# =========================
# TEST TEMPORANEO GITHUB STORAGE
# =========================

st.write("")

test_col_1, test_col_2, test_col_3 = st.columns([1.25, 1.25, 3.5])

with test_col_1:
    if st.button(
        "🧪  Test GitHub Storage",
        key="card_test_github_storage",
        use_container_width=True,
        help="Pagina temporanea per testare lettura watchlists.json dal branch data-watchlists"
    ):
        st.switch_page("pages/test_github_storage.py")
