import streamlit as st
from pathlib import Path

from utils.auth import require_login


# =========================
# PROTEZIONE LOGIN
# =========================
require_login()


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
                unsafe_allow_html=True,
            )


local_css(GLOBAL_CSS)
local_css(DASHBOARD_CSS)



# =========================
# TARGET ANALISTI STATE RESET
# =========================

def clear_target_navigation_state() -> None:
    """Open Target Analisti from Cockpit without reusing the last selected title."""
    for key in (
        "target_selected",
        "target_yf_symbol",
        "target_ticker",
        "target_tv_symbol",
        "target_name",
        "target_market",
        "target_currency",
        "target_source",
        "ticker_selezionato",
    ):
        st.session_state.pop(key, None)
    st.session_state["target_source"] = "cockpit"

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
    unsafe_allow_html=True,
)


# =========================
# MENU PRINCIPALE
# =========================
# IMPORTANT: use st.button + st.switch_page, not HTML <a> links.
# This preserves Streamlit session_state, including the login state.
col_watchlist_tv, col_portafoglio, col_allocazione = st.columns(3)

with col_watchlist_tv:
    if st.button(
        "📺 Watchlist TradingView\n\nMulti-tab, SMA 200W, drag & drop e grafici.",
        key="card_watchlist_tradingview",
        use_container_width=True,
    ):
        st.switch_page("pages/watchlist_tradingview.py")

with col_portafoglio:
    if st.button(
        "💼 Portafoglio\n\nArea dedicata alle posizioni reali.",
        key="card_portafoglio",
        use_container_width=True,
    ):
        st.switch_page("pages/portafoglio.py")

with col_allocazione:
    if st.button(
        "📊 Allocazione\n\nPesi, valute, mercati e concentrazione.",
        key="card_allocazione_portafoglio",
        use_container_width=True,
    ):
        st.switch_page("pages/allocazione_portafoglio.py")

col_target, col_logout, col_spacer = st.columns(3)

with col_target:
    if st.button(
        "🎯 Target Analisti\n\nTarget, upside e simulazione investimento.",
        key="card_target_analisti",
        use_container_width=True,
    ):
        clear_target_navigation_state()
        st.switch_page("pages/target_analisti.py")

with col_logout:
    if st.button(
        "🚪 Logout\n\nChiudi la sessione e torna al login.",
        key="card_logout",
        use_container_width=True,
    ):
        st.switch_page("pages/logout.py")
