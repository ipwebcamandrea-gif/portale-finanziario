from pathlib import Path
from html import escape

import streamlit as st

from components.watchlist_header import render_watchlist_header
from components.watchlist_tabs import render_watchlist_tabs
from components.watchlist_rows import render_watchlist_rows
from utils.watchlist_storage import (
    aggiorna_sessione_da_disco,
    salva_sessione_su_disco,
)


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
WATCHLIST_TV_CSS = ROOT_DIR / "css" / "watchlist_tradingview.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown("<style>" + file.read() + "</style>", unsafe_allow_html=True)


local_css(GLOBAL_CSS)
local_css(WATCHLIST_TV_CSS)


# =========================
# CSS INLINE SPECIFICO
# =========================

st.markdown(
    """
    <style>
    .tv-modern-back-button .stButton > button {
        min-height: 42px;
        border-radius: 12px;
        border: 1px solid rgba(0, 176, 255, 0.52);
        background:
            radial-gradient(circle at top left, rgba(0, 176, 255, 0.22), transparent 36%),
            linear-gradient(135deg, rgba(0, 176, 255, 0.16) 0%, rgba(22, 27, 34, 0.95) 100%);
        color: #e6edf3 !important;
        font-weight: 950;
        letter-spacing: -0.01em;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.05),
            0 0 14px rgba(0, 176, 255, 0.14);
    }

    .tv-modern-back-button .stButton > button:hover {
        border-color: rgba(0, 176, 255, 0.85);
        background:
            radial-gradient(circle at top left, rgba(0, 176, 255, 0.30), transparent 36%),
            linear-gradient(135deg, rgba(0, 176, 255, 0.22) 0%, rgba(22, 27, 34, 1) 100%);
        transform: translateY(-1px);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.06),
            0 0 18px rgba(0, 176, 255, 0.22);
    }

    div[class*="st-key-tv_normal_tab_"] .stButton > button,
    div[class*="st-key-tv_zone_tab_"] .stButton > button {
        min-height: 46px;
        width: 100%;
        border-radius: 10px;
        border: 1px solid rgba(48, 54, 61, 0.95);
        background: linear-gradient(180deg, #202733 0%, #151b24 100%);
        color: #e6edf3 !important;
        font-size: 0.98rem;
        font-weight: 900;
        letter-spacing: -0.01em;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
        transition: border-color 120ms ease, background 120ms ease, transform 120ms ease, box-shadow 120ms ease;
    }

    div[class*="st-key-tv_normal_tab_"] .stButton > button:hover,
    div[class*="st-key-tv_zone_tab_"] .stButton > button:hover {
        border-color: rgba(0, 176, 255, 0.65);
        background: linear-gradient(180deg, #27303a 0%, #1b222c 100%);
        color: #ffffff !important;
        transform: translateY(-1px);
    }

    div[class*="st-key-tv_active_tab_"] .stButton > button {
        border-color: rgba(0, 176, 255, 0.75);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.06),
            0 0 0 1px rgba(0, 176, 255, 0.16),
            0 0 14px rgba(0, 176, 255, 0.12);
    }

    div[class*="st-key-tv_zone_tab_"] .stButton > button {
        background:
            radial-gradient(circle at top right, rgba(255, 140, 0, 0.20), transparent 34%),
            linear-gradient(135deg, rgba(255, 140, 0, 0.15) 0%, rgba(255, 179, 71, 0.07) 100%);
        border-color: rgba(255, 140, 0, 0.82);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.04),
            0 0 15px rgba(255, 140, 0, 0.28);
    }

    div[class*="st-key-tv_tab_action_btn_"] .stButton > button {
        min-height: 34px;
        height: 34px;
        padding: 0.08rem 0.20rem;
        border-radius: 9px;
        font-size: 1.02rem;
        font-weight: 950;
    }

    .tv-delete-confirm-panel {
        margin: 0.55rem 0 0.80rem 0;
        padding: 0.72rem 0.85rem;
        border-radius: 12px;
        border: 1px solid rgba(239, 83, 80, 0.62);
        background:
            radial-gradient(circle at top right, rgba(239, 83, 80, 0.18), transparent 35%),
            linear-gradient(135deg, rgba(239, 83, 80, 0.12) 0%, rgba(22, 27, 34, 0.92) 100%);
        color: #e6edf3;
        font-weight: 850;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.04),
            0 0 14px rgba(239, 83, 80, 0.14);
    }

    .tv-delete-confirm-title {
        color: #ff8a80;
        font-size: 0.95rem;
        font-weight: 950;
        margin-bottom: 0.18rem;
    }

    .tv-delete-confirm-text {
        color: #9fb3d1;
        font-size: 0.82rem;
        font-weight: 700;
    }

    div[class*="st-key-tv_normal_row_"] {
        padding: 0.72rem 0.78rem 0.82rem 0.78rem;
        margin: 0.62rem 0;
        border-radius: 13px;
        border: 1px solid rgba(48, 54, 61, 0.72);
        background: rgba(13, 17, 23, 0.28);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
    }

    div[class*="st-key-tv_zone_row_"] {
        padding: 0.72rem 0.78rem 0.82rem 0.78rem;
        margin: 0.72rem 0;
        border-radius: 13px;
        border: 1px solid rgba(255, 140, 0, 0.82);
        background:
            radial-gradient(circle at top right, rgba(255, 140, 0, 0.20), transparent 34%),
            linear-gradient(135deg, rgba(255, 140, 0, 0.15) 0%, rgba(255, 179, 71, 0.07) 100%);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.04),
            0 0 15px rgba(255, 140, 0, 0.28);
    }

    div[class*="st-key-tv_zone_row_"]:hover {
        border-color: rgba(255, 179, 71, 0.98);
        background:
            radial-gradient(circle at top right, rgba(255, 140, 0, 0.25), transparent 34%),
            linear-gradient(135deg, rgba(255, 140, 0, 0.22) 0%, rgba(255, 179, 71, 0.10) 100%);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.05),
            0 0 18px rgba(255, 140, 0, 0.42);
    }

    .tv-cell-label {
        color: #9fb3d1;
        font-size: 0.68rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 0.18rem;
        white-space: nowrap;
    }

    .tv-cell-value {
        color: #e6edf3;
        font-size: 0.92rem;
        font-weight: 850;
        line-height: 1.25;
        word-break: break-word;
    }

    .tv-symbol-value {
        font-size: 1.02rem;
        font-weight: 950;
        letter-spacing: -0.025em;
    }

    .tv-symbol-note-inline {
        color: var(--text-muted);
        font-size: 0.72rem;
        font-weight: 650;
        margin-top: 0.10rem;
    }

    .tv-zone-text-inline { color: #f5c542; font-weight: 950; }
    .tv-positive-inline { color: #00c853; font-weight: 950; }
    .tv-negative-inline { color: #ff1744; font-weight: 950; }
    .tv-neutral-inline { color: var(--text-muted); font-weight: 850; }

    div[data-testid="stHorizontalBlock"] .stButton > button,
    div[data-testid="stHorizontalBlock"] [data-testid="stLinkButton"] > a {
        min-height: 30px;
        padding: 0.20rem 0.35rem;
        border-radius: 9px;
        font-weight: 950;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# RENDER HTML
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
# SESSION STATE
# =========================

if "tv_watchlists_data" not in st.session_state:
    aggiorna_sessione_da_disco()

if "tv_current_list" not in st.session_state:
    st.session_state["tv_current_list"] = st.session_state["tv_watchlists_data"]["active_watchlist"]

if "tv_show_create_panel" not in st.session_state:
    st.session_state["tv_show_create_panel"] = False

if "tv_add_symbol_nonce" not in st.session_state:
    st.session_state["tv_add_symbol_nonce"] = 0

if "tv_confirm_delete_tab" not in st.session_state:
    st.session_state["tv_confirm_delete_tab"] = False

if "tv_show_rename_panel" not in st.session_state:
    st.session_state["tv_show_rename_panel"] = False


# =========================
# PAGE HEADER + AZIONI ALTE
# =========================

render_watchlist_header()

# =========================
# TABS WATCHLIST + AZIONI
# =========================

render_watchlist_tabs()


# =========================
# LISTA ATTIVA
# =========================

current = st.session_state["tv_current_list"]
watchlists = st.session_state["tv_watchlists_data"]["watchlists"]

if current not in watchlists:
    current = list(watchlists.keys())[0]
    st.session_state["tv_current_list"] = current
    st.session_state["tv_watchlists_data"]["active_watchlist"] = current
    salva_sessione_su_disco()

symbols = watchlists.get(current, [])


# =========================
# AGGIUNGI SIMBOLO
# =========================

add_input_key = "tv_add_symbol_input_" + str(st.session_state["tv_add_symbol_nonce"])
add_col_1, add_col_2 = st.columns([5, 1])

with add_col_1:
    new_symbol = st.text_input(
        "Aggiungi simbolo",
        placeholder="Es. AAPL, MSFT, TSLA, SWDA.MI",
        label_visibility="collapsed",
        key=add_input_key,
    ).upper().strip()

with add_col_2:
    if st.button("Aggiungi", key="tv_add_symbol_btn", use_container_width=True):
        if not new_symbol:
            st.warning("Inserisci un simbolo valido.")
        elif new_symbol in st.session_state["tv_watchlists_data"]["watchlists"][current]:
            st.warning("Simbolo gia presente nella watchlist.")
        else:
            st.session_state["tv_watchlists_data"]["watchlists"][current].append(new_symbol)
            st.session_state["tv_add_symbol_nonce"] += 1
            st.session_state["tv_confirm_delete_tab"] = False
            st.session_state["tv_show_rename_panel"] = False
            salva_sessione_su_disco()
            st.cache_data.clear()
            st.success(new_symbol + " aggiunto.")
            st.rerun()


symbols = st.session_state["tv_watchlists_data"]["watchlists"].get(current, [])

if not symbols:
    st.markdown(
        """
        <div class="tv-empty">
            Nessun simbolo presente in questa watchlist. Aggiungi un simbolo per iniziare.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# =========================
# RENDER RIGHE STREAMLIT NATIVE
# =========================

render_watchlist_rows(current, symbols)
