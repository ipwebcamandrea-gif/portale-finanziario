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
WATCHLIST_FILE = ROOT_DIR / "watchlist.txt"

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
# FUNZIONI
# =========================

def carica_ticker_da_file():
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as file:
            return [
                line.strip().upper()
                for line in file.readlines()
                if line.strip()
            ]

    return []


def render_status_card(label, value, note):
    st.markdown(
        f"""
        <div class="cockpit-status-card">
            <div class="status-label">{label}</div>
            <div class="status-value">{value}</div>
            <div class="status-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# DATI BASE
# =========================

lista_ticker = carica_ticker_da_file()
numero_ticker = len(lista_ticker)

if "lista_tickers" not in st.session_state:
    st.session_state["lista_tickers"] = lista_ticker


# =========================
# HEADER
# =========================

st.markdown(
    """
    <div class="cockpit-header">
        <div class="cockpit-eyebrow">FinancePortal 2026 · V1.1 Development</div>
        <div class="main-title">Portafoglio Cockpit</div>
        <div class="subtitle">
            Centro di controllo del monitor finanziario. Da qui puoi aprire la Watchlist,
            la nuova Watchlist TradingView, consultare il Portafoglio e gestire la sessione.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# STATUS
# =========================

col_status_1, col_status_2, col_status_3 = st.columns(3)

with col_status_1:
    render_status_card(
        "Watchlist",
        numero_ticker,
        "Ticker caricati da watchlist.txt"
    )

with col_status_2:
    render_status_card(
        "Versione",
        "V1.1",
        "Branch dev-v1.1.0"
    )

with col_status_3:
    render_status_card(
        "Sessione",
        "Attiva",
        "Utente autenticato"
    )


# =========================
# MENU PRINCIPALE
# =========================

st.markdown(
    """
    <div class="cockpit-info-panel">
        <div class="cockpit-info-title">Menu principale</div>
        <div class="cockpit-info-text">
            Usa le card qui sotto per navigare. Il grafico dettaglio non è nel menu:
            si apre solo dalle Watchlist tramite il pulsante sul singolo ticker.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

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
# INFO
# =========================

st.markdown(
    """
    <div class="cockpit-info-panel">
        <div class="cockpit-info-title">Navigazione semplificata</div>
        <div class="cockpit-info-text">
            Il menu laterale automatico di Streamlit è nascosto. La navigazione principale
            passa dal Cockpit, mentre le pagine operative gestiscono i propri ritorni.
            La Watchlist TradingView è una nuova pagina separata e non modifica la Watchlist attuale.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
