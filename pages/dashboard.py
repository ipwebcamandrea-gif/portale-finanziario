import streamlit as st
from pathlib import Path
from html import escape

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
# CARD HTML CLICKABLE
# =========================
def cockpit_card(icon: str, title: str, description: str, href: str) -> str:
    return f"""
    <a class="cockpit-card-link" href="{escape(href, quote=True)}" target="_self">
        <div class="cockpit-menu-card">
            <div class="cockpit-card-title">{escape(icon)} {escape(title)}</div>
            <div class="cockpit-card-description">{escape(description)}</div>
        </div>
    </a>
    """


cards_html = "".join(
    [
        cockpit_card(
            "📺",
            "Watchlist TradingView",
            "Multi-tab, SMA 200W, drag & drop e grafici.",
            "watchlist_tradingview",
        ),
        cockpit_card(
            "💼",
            "Portafoglio",
            "Area dedicata alle posizioni reali.",
            "portafoglio",
        ),
        cockpit_card(
            "📊",
            "Allocazione",
            "Pesi, valute, mercati e concentrazione.",
            "allocazione_portafoglio",
        ),
        cockpit_card(
            "🚪",
            "Logout",
            "Chiudi la sessione e torna al login.",
            "logout",
        ),
    ]
)

st.markdown(
    f"""
    <div class="cockpit-card-grid">
        {cards_html}
    </div>
    """,
    unsafe_allow_html=True,
)
