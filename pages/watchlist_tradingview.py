import re
from pathlib import Path
from html import escape

import streamlit as st

from utils.symbols import slug_safe, url_tradingview
from utils.formatting import (
    formatta_prezzo,
    formatta_percentuale,
    classe_percentuale,
    classe_zona_sma,
    cell_html,
)
from utils.market_data import (
    get_stock_metrics,
    is_in_sma200_zone,
    watchlist_has_sma200_zone,
)
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
    unsafe_allow_html=True
)


# =========================
# ORDINAMENTO SENZA COMPONENTI ESTERNI
# =========================

def sposta_elemento(lista, elemento, direzione):
    lista_nuova = list(lista)

    if elemento not in lista_nuova:
        return lista_nuova

    indice = lista_nuova.index(elemento)
    nuovo_indice = indice + direzione

    if nuovo_indice < 0 or nuovo_indice >= len(lista_nuova):
        return lista_nuova

    lista_nuova[indice], lista_nuova[nuovo_indice] = (
        lista_nuova[nuovo_indice],
        lista_nuova[indice]
    )

    return lista_nuova


def sposta_watchlist(nome_lista, direzione):
    data = st.session_state["tv_watchlists_data"]
    watchlists = data["watchlists"]
    nomi = list(watchlists.keys())
    nuovi_nomi = sposta_elemento(nomi, nome_lista, direzione)

    if nuovi_nomi == nomi:
        return

    nuova_struttura = {}

    for nome in nuovi_nomi:
        nuova_struttura[nome] = watchlists[nome]

    data["watchlists"] = nuova_struttura
    data["active_watchlist"] = st.session_state["tv_current_list"]
    salva_sessione_su_disco()


def sposta_simbolo(nome_lista, simbolo, direzione):
    data = st.session_state["tv_watchlists_data"]
    simboli = data["watchlists"].get(nome_lista, [])
    nuovi_simboli = sposta_elemento(simboli, simbolo, direzione)

    if nuovi_simboli == simboli:
        return

    data["watchlists"][nome_lista] = nuovi_simboli
    salva_sessione_su_disco()


def elimina_watchlist_attiva():
    data = st.session_state["tv_watchlists_data"]
    watchlists = data["watchlists"]
    current = st.session_state["tv_current_list"]

    if len(watchlists) <= 1:
        st.warning("Non puoi eliminare l'unica watchlist rimasta.")
        return

    nomi = list(watchlists.keys())
    indice_corrente = nomi.index(current) if current in nomi else 0

    if current in watchlists:
        del watchlists[current]

    nuovi_nomi = list(watchlists.keys())
    nuovo_indice = min(indice_corrente, len(nuovi_nomi) - 1)
    nuovo_corrente = nuovi_nomi[nuovo_indice]

    st.session_state["tv_current_list"] = nuovo_corrente
    data["active_watchlist"] = nuovo_corrente
    st.session_state["tv_confirm_delete_tab"] = False
    salva_sessione_su_disco()
    st.cache_data.clear()


def rinomina_watchlist_attiva(nuovo_nome):
    data = st.session_state["tv_watchlists_data"]
    watchlists = data["watchlists"]
    current = st.session_state["tv_current_list"]

    nuovo_nome = str(nuovo_nome or "").strip()

    if not nuovo_nome:
        st.warning("Inserisci un nome valido.")
        return False

    if nuovo_nome == current:
        st.session_state["tv_show_rename_panel"] = False
        return True

    if nuovo_nome in watchlists:
        st.warning("Esiste gia una watchlist con questo nome.")
        return False

    nuova_struttura = {}

    for nome, simboli in watchlists.items():
        if nome == current:
            nuova_struttura[nuovo_nome] = simboli
        else:
            nuova_struttura[nome] = simboli

    data["watchlists"] = nuova_struttura
    data["active_watchlist"] = nuovo_nome
    st.session_state["tv_current_list"] = nuovo_nome
    st.session_state["tv_show_rename_panel"] = False

    salva_sessione_su_disco()
    st.cache_data.clear()

    return True


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
        unsafe_allow_html=True
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
        unsafe_allow_html=True
    )


def render_row_streamlit(symbol, metrics, current):
    dist_pct = metrics["dist_pct"]
    daily_pct = metrics["daily_change_pct"]
    sma200w = metrics.get("sma200w")

    prezzo = formatta_prezzo(metrics["last_price"], metrics["currency"])
    sma200w_testo = formatta_prezzo(sma200w, metrics["currency"])
    distanza = formatta_percentuale(dist_pct)
    daily = formatta_percentuale(daily_pct)

    daily_class = classe_percentuale(daily_pct)
    dist_class = classe_zona_sma(dist_pct)
    in_zone = is_in_sma200_zone(dist_pct)
    zone_note = "Zona SMA200W" if in_zone else "Monitoraggio"

    row_kind = "zone" if in_zone else "normal"
    row_key = "tv_" + row_kind + "_row_" + slug_safe(current) + "_" + slug_safe(symbol)

    with st.container(key=row_key):
        row_col_1, row_col_2, row_col_3, row_col_4, row_col_5, row_col_6 = st.columns(
            [1.40, 1.00, 1.05, 1.18, 0.82, 1.55],
            vertical_alignment="center"
        )

        with row_col_1:
            st.markdown(
                '<div class="tv-cell-label">Ticker</div>'
                f'<div class="tv-cell-value tv-symbol-value">{escape(symbol)}</div>'
                f'<div class="tv-symbol-note-inline">{zone_note}</div>',
                unsafe_allow_html=True
            )

        with row_col_2:
            st.markdown(cell_html("Prezzo", prezzo), unsafe_allow_html=True)

        with row_col_3:
            st.markdown(cell_html("SMA 200W", sma200w_testo), unsafe_allow_html=True)

        with row_col_4:
            st.markdown(cell_html("Distanza SMA200W", distanza, dist_class), unsafe_allow_html=True)

        with row_col_5:
            st.markdown(cell_html("Daily", daily, daily_class), unsafe_allow_html=True)

        with row_col_6:
            st.markdown('<div class="tv-cell-label">Azioni</div>', unsafe_allow_html=True)
            action_col_0, action_col_1, action_col_2, action_col_3, action_col_4 = st.columns(5)

            with action_col_0:
                st.link_button(
                    "📊",
                    url_tradingview(symbol),
                    use_container_width=True,
                    help="Apri TradingView esterno"
                )

            with action_col_1:
                if st.button(
                    "📈",
                    key="tv_graph_" + symbol + "_" + current,
                    use_container_width=True,
                    help="Apri grafico tecnico weekly"
                ):
                    st.session_state["ticker_selezionato"] = symbol
                    st.switch_page("pages/grafico.py")

            with action_col_2:
                if st.button("▲", key="tv_up_" + symbol + "_" + current, use_container_width=True, help="Sposta simbolo in alto"):
                    sposta_simbolo(current, symbol, -1)
                    st.rerun()

            with action_col_3:
                if st.button("▼", key="tv_down_" + symbol + "_" + current, use_container_width=True, help="Sposta simbolo in basso"):
                    sposta_simbolo(current, symbol, 1)
                    st.rerun()

            with action_col_4:
                if st.button("×", key="tv_delete_" + symbol + "_" + current, use_container_width=True, help="Elimina simbolo dalla watchlist"):
                    if symbol in st.session_state["tv_watchlists_data"]["watchlists"][current]:
                        st.session_state["tv_watchlists_data"]["watchlists"][current].remove(symbol)
                        salva_sessione_su_disco()
                        st.cache_data.clear()
                        st.rerun()


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

header_col_1, header_col_2 = st.columns([5.0, 1.35], vertical_alignment="center")

with header_col_1:
    render_header()
    render_persistence_note()

with header_col_2:
    st.markdown('<div class="tv-modern-back-button">', unsafe_allow_html=True)
    if st.button("← Cockpit", key="tv_back_cockpit", use_container_width=True):
        st.switch_page("pages/dashboard.py")
    st.markdown('</div>', unsafe_allow_html=True)


# =========================
# TABS WATCHLIST + AZIONI
# =========================

watchlists = st.session_state["tv_watchlists_data"]["watchlists"]
watchlist_names = list(watchlists.keys())

cols = st.columns(len(watchlist_names) + 1)

for idx, name in enumerate(watchlist_names):
    in_zone = watchlist_has_sma200_zone(name)
    is_active = name == st.session_state["tv_current_list"]

    tab_kind = "zone" if in_zone else "normal"
    active_part = "_active_tab" if is_active else ""
    tab_wrap_key = "tv_" + tab_kind + "_tab" + active_part + "_" + slug_safe(name)
    tab_label = ("▶ " if is_active else "") + name

    with cols[idx]:
        with st.container(key=tab_wrap_key):
            if st.button(tab_label, key="tv_tab_btn_" + slug_safe(name), use_container_width=True):
                st.session_state["tv_current_list"] = name
                st.session_state["tv_watchlists_data"]["active_watchlist"] = name
                st.session_state["tv_confirm_delete_tab"] = False
                st.session_state["tv_show_rename_panel"] = False
                salva_sessione_su_disco()
                st.rerun()

with cols[-1]:
    plus_col, rename_col, minus_col = st.columns(3, gap="small")

    with plus_col:
        with st.container(key="tv_tab_action_btn_plus"):
            if st.button("+", key="tv_create_toggle", use_container_width=True, help="Crea nuova watchlist"):
                st.session_state["tv_show_create_panel"] = not st.session_state["tv_show_create_panel"]
                st.session_state["tv_confirm_delete_tab"] = False
                st.session_state["tv_show_rename_panel"] = False
                st.rerun()

    with rename_col:
        with st.container(key="tv_tab_action_btn_rename"):
            if st.button("✎", key="tv_rename_current_list", use_container_width=True, help="Rinomina la watchlist attiva"):
                st.session_state["tv_show_rename_panel"] = not st.session_state["tv_show_rename_panel"]
                st.session_state["tv_show_create_panel"] = False
                st.session_state["tv_confirm_delete_tab"] = False
                st.rerun()

    with minus_col:
        with st.container(key="tv_tab_action_btn_minus"):
            if st.button("−", key="tv_delete_current_list", use_container_width=True, help="Elimina la watchlist attiva"):
                st.session_state["tv_confirm_delete_tab"] = True
                st.session_state["tv_show_create_panel"] = False
                st.session_state["tv_show_rename_panel"] = False
                st.rerun()

move_tab_col_1, move_tab_col_2, refresh_col, spacer_col = st.columns([0.55, 0.55, 1.1, 4.8])

with move_tab_col_1:
    if st.button("◀", key="tv_move_tab_left", use_container_width=True, help="Sposta la watchlist attiva a sinistra"):
        st.session_state["tv_confirm_delete_tab"] = False
        st.session_state["tv_show_rename_panel"] = False
        sposta_watchlist(st.session_state["tv_current_list"], -1)
        st.rerun()

with move_tab_col_2:
    if st.button("▶", key="tv_move_tab_right", use_container_width=True, help="Sposta la watchlist attiva a destra"):
        st.session_state["tv_confirm_delete_tab"] = False
        st.session_state["tv_show_rename_panel"] = False
        sposta_watchlist(st.session_state["tv_current_list"], 1)
        st.rerun()

with refresh_col:
    if st.button("Aggiorna dati", key="tv_refresh_data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# =========================
# CONFERMA ELIMINAZIONE WATCHLIST
# =========================

if st.session_state.get("tv_confirm_delete_tab", False):
    current_confirm = st.session_state.get("tv_current_list", "")

    st.markdown(
        f"""
        <div class="tv-delete-confirm-panel">
            <div class="tv-delete-confirm-title">Conferma eliminazione watchlist</div>
            <div class="tv-delete-confirm-text">
                Vuoi eliminare definitivamente la watchlist <b>{escape(current_confirm)}</b> e tutti i simboli contenuti?
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    confirm_col_1, confirm_col_2, confirm_col_3 = st.columns([1.25, 1.0, 4.75])

    with confirm_col_1:
        if st.button("Elimina", key="tv_confirm_delete_current_list", use_container_width=True):
            elimina_watchlist_attiva()
            st.rerun()

    with confirm_col_2:
        if st.button("Annulla", key="tv_cancel_delete_current_list", use_container_width=True):
            st.session_state["tv_confirm_delete_tab"] = False
            st.rerun()



# =========================
# RINOMINA WATCHLIST
# =========================

if st.session_state.get("tv_show_rename_panel", False):
    current_rename = st.session_state.get("tv_current_list", "")

    st.markdown(
        f"""
        <div class="tv-delete-confirm-panel">
            <div class="tv-delete-confirm-title">Rinomina watchlist</div>
            <div class="tv-delete-confirm-text">
                Nome attuale: <b>{escape(current_rename)}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    rename_col_1, rename_col_2, rename_col_3, rename_col_4 = st.columns([3, 1, 1, 3])

    with rename_col_1:
        nuovo_nome_watchlist = st.text_input(
            "Nuovo nome watchlist",
            value=current_rename,
            key="tv_rename_list_name_" + slug_safe(current_rename),
            label_visibility="collapsed"
        ).strip()

    with rename_col_2:
        if st.button("Salva", key="tv_confirm_rename_current_list", use_container_width=True):
            if rinomina_watchlist_attiva(nuovo_nome_watchlist):
                st.success("Watchlist rinominata.")
                st.rerun()

    with rename_col_3:
        if st.button("Annulla", key="tv_cancel_rename_current_list", use_container_width=True):
            st.session_state["tv_show_rename_panel"] = False
            st.rerun()

# =========================
# CREA NUOVA WATCHLIST
# =========================

if st.session_state["tv_show_create_panel"]:
    create_col_1, create_col_2, create_col_3 = st.columns([3, 1, 1])

    with create_col_1:
        new_list_name = st.text_input("Nome nuova watchlist", placeholder="Esempio: Tech USA, ETF, Italia", key="tv_new_list_name").strip()

    with create_col_2:
        st.write("")
        st.write("")

        if st.button("Crea", key="tv_create_list", use_container_width=True):
            if not new_list_name:
                st.warning("Inserisci un nome valido.")
            elif new_list_name in st.session_state["tv_watchlists_data"]["watchlists"]:
                st.warning("Questa watchlist esiste gia.")
            else:
                st.session_state["tv_watchlists_data"]["watchlists"][new_list_name] = []
                st.session_state["tv_current_list"] = new_list_name
                st.session_state["tv_watchlists_data"]["active_watchlist"] = new_list_name
                st.session_state["tv_show_create_panel"] = False
                st.session_state["tv_confirm_delete_tab"] = False
                st.session_state["tv_show_rename_panel"] = False
                salva_sessione_su_disco()
                st.success("Watchlist creata.")
                st.rerun()

    with create_col_3:
        st.write("")
        st.write("")

        if st.button("Annulla", key="tv_cancel_create", use_container_width=True):
            st.session_state["tv_show_create_panel"] = False
            st.rerun()


# =========================
# LISTA ATTIVA
# =========================

current = st.session_state["tv_current_list"]
watchlists = st.session_state["tv_watchlists_data"]["watchlists"]

if current not in watchlists:
    current = list(watchlists.keys())[0]
    st.session_state["tv_current_list"] = current

symbols = watchlists.get(current, [])


# =========================
# AGGIUNGI SIMBOLO
# =========================

add_input_key = "tv_add_symbol_input_" + str(st.session_state["tv_add_symbol_nonce"])
add_col_1, add_col_2 = st.columns([5, 1])

with add_col_1:
    new_symbol = st.text_input("Aggiungi simbolo", placeholder="Es. AAPL, MSFT, TSLA, SWDA.MI", label_visibility="collapsed", key=add_input_key).upper().strip()

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
        unsafe_allow_html=True
    )
    st.stop()


# =========================
# RENDER RIGHE STREAMLIT NATIVE
# =========================

for symbol in list(symbols):
    metrics = get_stock_metrics(symbol)
    render_row_streamlit(symbol, metrics, current)
