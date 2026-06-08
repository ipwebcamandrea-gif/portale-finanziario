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
# FUNZIONI DI SUPPORTO
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


def render_menu_card(icon, title, text, accent_class=""):
    st.markdown(
        f"""
        <div class="cockpit-card {accent_class}">
            <div class="cockpit-card-icon">{icon}</div>
            <div class="cockpit-card-title">{title}</div>
            <div class="cockpit-card-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# DATI BASE COCKPIT
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
            consultare il tuo Portafoglio e gestire la sessione di lavoro.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# STATUS STRIP
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
        "Ambiente di sviluppo su dev-v1.1.0"
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

st.markdown("")

col_watchlist, col_portafoglio, col_logout = st.columns(3)

with col_watchlist:
    render_menu_card(
        "📊",
        "Watchlist",
        "Apri la lista dei ticker monitorati, controlla prezzi, SMA 200D, stato tecnico e grafici.",
        "cockpit-card-accent-green"
    )

    if st.button("Apri Watchlist", key="btn_open_watchlist"):
        st.switch_page("pages/watchlist.py")


with col_portafoglio:
    render_menu_card(
        "💼",
        "Portafoglio",
        "Consulta l'area dedicata alle posizioni reali. La sezione è pronta per gli sviluppi successivi.",
        "cockpit-card-accent-yellow"
    )

    if st.button("Apri Portafoglio", key="btn_open_portafoglio"):
        st.switch_page("pages/portafoglio.py")


with col_logout:
    render_menu_card(
        "🚪",
        "Logout",
        "Chiudi la sessione corrente e torna alla schermata di accesso.",
        "cockpit-card-accent-red"
    )

    if st.button("Esci", key="btn_open_logout"):
        st.switch_page("pages/logout.py")


# =========================
# INFO PANEL
# =========================

st.markdown(
    """
    <div class="cockpit-info-panel">
        <div class="cockpit-info-title">Navigazione semplificata</div>
        <div class="cockpit-info-text">
            Il menu laterale automatico di Streamlit è stato nascosto.
            La navigazione principale ora passa da questo cockpit, mentre il grafico dettagliato
            resta accessibile solo dal pulsante 📈 del singolo ticker nella Watchlist.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
