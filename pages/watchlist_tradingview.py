import json
from pathlib import Path

import streamlit as st
import yfinance as yf

try:
    from streamlit_sortables import sort_items
except Exception:
    sort_items = None


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
WATCHLISTS_JSON = ROOT_DIR / "watchlists.json"

GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
WATCHLIST_TV_CSS = ROOT_DIR / "css" / "watchlist_tradingview.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(
                "<style>" + file.read() + "</style>",
                unsafe_allow_html=True
            )


local_css(GLOBAL_CSS)
local_css(WATCHLIST_TV_CSS)


# =========================
# DEFAULT DATA
# =========================

DEFAULT_DATA = {
    "version": 1,
    "active_watchlist": "Default",
    "watchlists": {
        "Default": ["AAPL", "MSFT", "GOOGL"],
        "Finanza": ["JPM", "BAC", "V", "MA"],
        "ETF": ["SWDA.MI", "EIMI.MI"]
    }
}


# =========================
# PERSISTENZA JSON LOCALE
# =========================

def normalizza_dati_watchlists(data):
    if not isinstance(data, dict):
        return DEFAULT_DATA.copy()

    if "watchlists" not in data or not isinstance(data["watchlists"], dict):
        # Compatibilita con formato semplice: {"Default": ["AAPL"]}
        if all(isinstance(value, list) for value in data.values()):
            data = {
                "version": 1,
                "active_watchlist": list(data.keys())[0] if data else "Default",
                "watchlists": data
            }
        else:
            return DEFAULT_DATA.copy()

    if "version" not in data:
        data["version"] = 1

    watchlists = data.get("watchlists", {})

    if not watchlists:
        watchlists = {"Default": []}
        data["watchlists"] = watchlists

    # Pulisce nomi liste e ticker
    watchlists_pulite = {}

    for nome_lista, simboli in watchlists.items():
        nome_pulito = str(nome_lista).strip()

        if not nome_pulito:
            continue

        if not isinstance(simboli, list):
            simboli = []

        simboli_puliti = []

        for simbolo in simboli:
            simbolo_pulito = str(simbolo).strip().upper()

            if simbolo_pulito and simbolo_pulito not in simboli_puliti:
                simboli_puliti.append(simbolo_pulito)

        watchlists_pulite[nome_pulito] = simboli_puliti

    if not watchlists_pulite:
        watchlists_pulite = {"Default": []}

    data["watchlists"] = watchlists_pulite

    active = data.get("active_watchlist")

    if active not in watchlists_pulite:
        data["active_watchlist"] = list(watchlists_pulite.keys())[0]

    return data


def carica_watchlists_da_json():
    if not WATCHLISTS_JSON.exists():
        salva_watchlists_su_json(DEFAULT_DATA)
        return DEFAULT_DATA.copy()

    try:
        with open(WATCHLISTS_JSON, "r", encoding="utf-8") as file:
            data = json.load(file)

        return normalizza_dati_watchlists(data)

    except Exception:
        return DEFAULT_DATA.copy()


def salva_watchlists_su_json(data):
    data = normalizza_dati_watchlists(data)

    with open(WATCHLISTS_JSON, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def aggiorna_sessione_da_disco():
    st.session_state["tv_watchlists_data"] = carica_watchlists_da_json()
    st.session_state["tv_current_list"] = st.session_state["tv_watchlists_data"].get(
        "active_watchlist",
        list(st.session_state["tv_watchlists_data"]["watchlists"].keys())[0]
    )


def salva_sessione_su_disco():
    data = st.session_state["tv_watchlists_data"]
    data["active_watchlist"] = st.session_state.get("tv_current_list")
    salva_watchlists_su_json(data)


# =========================
# METRICHE FINANZIARIE
# =========================

@st.cache_data(ttl=900, show_spinner=False)
def get_stock_metrics(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info

        last_price = info.get("last_price", None)
        previous_close = info.get("previous_close", None)
        currency = info.get("currency", "")

        daily_change_pct = None

        if last_price is not None and previous_close is not None and previous_close != 0:
            daily_change_pct = ((last_price - previous_close) / previous_close) * 100

        hist = ticker.history(period="10y", interval="1wk")

        sma200 = None
        dist_pct = None

        if hist is not None and not hist.empty and "Close" in hist.columns:
            hist = hist.dropna(subset=["Close"])

            if len(hist) >= 200:
                sma200 = hist["Close"].rolling(200).mean().iloc[-1]

                if sma200 is not None and sma200 != 0 and last_price is not None:
                    dist_pct = ((last_price - sma200) / sma200) * 100

        if last_price is not None:
            last_price = float(last_price)

        if daily_change_pct is not None:
            daily_change_pct = float(daily_change_pct)

        if sma200 is not None:
            sma200 = float(sma200)

        if dist_pct is not None:
            dist_pct = float(dist_pct)

        return {
            "last_price": last_price,
            "daily_change_pct": daily_change_pct,
            "sma200w": sma200,
            "dist_pct": dist_pct,
            "currency": currency or ""
        }

    except Exception:
        return {
            "last_price": None,
            "daily_change_pct": None,
            "sma200w": None,
            "dist_pct": None,
            "currency": ""
        }


def is_in_sma200_zone(dist_pct):
    return dist_pct is not None and -10 <= dist_pct <= 10


def watchlist_has_sma200_zone(name):
    symbols = st.session_state["tv_watchlists_data"]["watchlists"].get(name, [])

    for symbol in symbols:
        metrics = get_stock_metrics(symbol)

        if is_in_sma200_zone(metrics["dist_pct"]):
            return True

    return False


# =========================
# FORMATTAZIONE
# =========================

def formatta_prezzo(value, currency):
    if value is None:
        return "N/D"

    suffix = " " + currency if currency else ""

    return f"{value:.2f}{suffix}"


def formatta_percentuale(value):
    if value is None:
        return "N/D"

    return f"{value:.2f} %"


def classe_percentuale(value):
    if value is None:
        return "tv-neutral"

    if value > 0:
        return "tv-positive"

    if value < 0:
        return "tv-negative"

    return "tv-neutral"


def classe_zona_sma(value):
    if is_in_sma200_zone(value):
        return "tv-zone-text"

    return classe_percentuale(value)


def render_header():
    st.markdown(
        """
        <div class="tv-page-header">
            <div class="tv-page-title">Watchlist TradingView</div>
            <div class="tv-page-subtitle">
                Multi-watchlist in stile TradingView con tab, ordinamento manuale,
                distanza da SMA 200W e apertura diretta del grafico weekly.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_persistence_note():
    st.markdown(
        """
        <div class="tv-persistence-note">
            <div class="tv-persistence-title">Modalita JSON locale</div>
            <div class="tv-persistence-text">
                In questa prima versione le modifiche vengono salvate su watchlists.json
                nell'ambiente dell'app. In futuro potremo collegare lo stesso JSON a GitHub API
                per persistenza definitiva su repository.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_active_list_card(current, symbols):
    st.markdown(
        f"""
        <div class="tv-active-list-card">
            <div class="tv-active-list-label">Lista attiva</div>
            <div class="tv-active-list-name">{current}</div>
            <div class="tv-active-list-note">
                {len(symbols)} simboli monitorati · dati Yahoo Finance · SMA 200W su timeframe weekly.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_row(symbol, metrics):
    dist_pct = metrics["dist_pct"]
    daily_pct = metrics["daily_change_pct"]
    row_class = "tv-row tv-row-zone" if is_in_sma200_zone(dist_pct) else "tv-row"

    prezzo = formatta_prezzo(metrics["last_price"], metrics["currency"])
    distanza = formatta_percentuale(dist_pct)
    daily = formatta_percentuale(daily_pct)

    daily_class = classe_percentuale(daily_pct)
    dist_class = classe_zona_sma(dist_pct)

    zone_note = "Zona SMA200W" if is_in_sma200_zone(dist_pct) else "Monitoraggio"

    html = (
        f'<div class="{row_class}">'
        '<div class="tv-row-grid">'
        '<div class="tv-symbol-block">'
        f'<div class="tv-symbol">{symbol}</div>'
        f'<div class="tv-symbol-note">{zone_note}</div>'
        '</div>'
        '<div>'
        '<div class="tv-metric-label">Prezzo</div>'
        f'<div class="tv-metric-value tv-price">{prezzo}</div>'
        '</div>'
        '<div>'
        '<div class="tv-metric-label">Distanza SMA200W</div>'
        f'<div class="tv-metric-value {dist_class}">{distanza}</div>'
        '</div>'
        '<div>'
        '<div class="tv-metric-label">Daily</div>'
        f'<div class="tv-metric-value {daily_class}">{daily}</div>'
        '</div>'
        '<div>'
        '<div class="tv-metric-label">Azioni</div>'
        '<div class="tv-actions-note">Grafico / elimina</div>'
        '</div>'
        '</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


# =========================
# SESSION STATE
# =========================

if "tv_watchlists_data" not in st.session_state:
    aggiorna_sessione_da_disco()

if "tv_current_list" not in st.session_state:
    st.session_state["tv_current_list"] = st.session_state["tv_watchlists_data"]["active_watchlist"]

if "tv_show_create_panel" not in st.session_state:
    st.session_state["tv_show_create_panel"] = False


# =========================
# PAGE HEADER
# =========================

render_header()
render_persistence_note()


# =========================
# NAVIGAZIONE
# =========================

st.markdown(
    """
    <div class="tv-topbar">
        <div class="tv-topbar-title">Navigazione</div>
        <div class="tv-topbar-text">
            Torna al Cockpit oppure apri il grafico weekly direttamente dalla riga del simbolo.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

nav_col_1, nav_col_2 = st.columns([1.2, 4.8])

with nav_col_1:
    if st.button("Torna al Cockpit", key="tv_back_cockpit"):
        st.switch_page("pages/dashboard.py")


# =========================
# TABS WATCHLIST
# =========================

st.markdown(
    """
    <div class="tv-tabs-panel">
        <div class="tv-tabs-title">Watchlist</div>
        <div class="tv-tabs-subtitle">
            Seleziona una lista, crea nuove tab o riordina i nomi delle watchlist.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

watchlists = st.session_state["tv_watchlists_data"]["watchlists"]
watchlist_names = list(watchlists.keys())

if sort_items is not None and len(watchlist_names) > 1:
    sorted_tab_names = sort_items(
        watchlist_names,
        direction="horizontal",
        key="tv_sortable_tabs"
    )

    if sorted_tab_names and sorted_tab_names != watchlist_names:
        nuova_struttura = {}

        for name in sorted_tab_names:
            if name in watchlists:
                nuova_struttura[name] = watchlists[name]

        st.session_state["tv_watchlists_data"]["watchlists"] = nuova_struttura

        if st.session_state["tv_current_list"] not in nuova_struttura:
            st.session_state["tv_current_list"] = list(nuova_struttura.keys())[0]

        st.session_state["tv_watchlists_data"]["active_watchlist"] = st.session_state["tv_current_list"]
        salva_sessione_su_disco()
        st.rerun()

elif sort_items is None:
    st.info("Ordinamento tab non disponibile: verifica streamlit-sortables in requirements.txt.")

watchlists = st.session_state["tv_watchlists_data"]["watchlists"]
watchlist_names = list(watchlists.keys())

cols = st.columns(len(watchlist_names) + 1)

for idx, name in enumerate(watchlist_names):
    is_active = name == st.session_state["tv_current_list"]
    in_zone = watchlist_has_sma200_zone(name)

    prefix = "▶ " if is_active else ""
    zone_mark = "■ " if in_zone else ""
    label = prefix + zone_mark + name

    if cols[idx].button(label, key="tv_tab_" + name, use_container_width=True):
        st.session_state["tv_current_list"] = name
        st.session_state["tv_watchlists_data"]["active_watchlist"] = name
        salva_sessione_su_disco()
        st.rerun()

if cols[-1].button("+", key="tv_create_toggle", use_container_width=True):
    st.session_state["tv_show_create_panel"] = not st.session_state["tv_show_create_panel"]
    st.rerun()


# =========================
# CREA NUOVA WATCHLIST
# =========================

if st.session_state["tv_show_create_panel"]:
    st.markdown(
        """
        <div class="tv-create-panel">
            <div class="tv-create-title">Crea nuova watchlist</div>
            <div class="tv-create-text">
                Inserisci il nome della nuova tab. La lista verra salvata nel JSON locale.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    create_col_1, create_col_2, create_col_3 = st.columns([3, 1, 1])

    with create_col_1:
        new_list_name = st.text_input(
            "Nome nuova watchlist",
            placeholder="Esempio: Tech USA, ETF, Italia",
            key="tv_new_list_name"
        ).strip()

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

render_active_list_card(current, symbols)


# =========================
# AGGIUNGI SIMBOLO
# =========================

st.markdown(
    """
    <div class="tv-add-panel">
        <div class="tv-add-title">Aggiungi simbolo</div>
        <div class="tv-add-subtitle">
            Usa simboli compatibili Yahoo Finance, ad esempio AAPL, MSFT, NVDA, SWDA.MI.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

add_col_1, add_col_2 = st.columns([5, 1])

with add_col_1:
    new_symbol = st.text_input(
        "Aggiungi simbolo",
        placeholder="Es. AAPL, MSFT, TSLA, SWDA.MI",
        label_visibility="collapsed",
        key="tv_add_symbol_input"
    ).upper().strip()

with add_col_2:
    if st.button("Aggiungi", key="tv_add_symbol_btn", use_container_width=True):
        if not new_symbol:
            st.warning("Inserisci un simbolo valido.")
        elif new_symbol in st.session_state["tv_watchlists_data"]["watchlists"][current]:
            st.warning("Simbolo gia presente nella watchlist.")
        else:
            st.session_state["tv_watchlists_data"]["watchlists"][current].append(new_symbol)
            salva_sessione_su_disco()
            st.cache_data.clear()
            st.success(new_symbol + " aggiunto.")
            st.rerun()


# =========================
# TOOLBAR RIGHE
# =========================

st.markdown(
    """
    <div class="tv-rows-toolbar">
        <div class="tv-rows-title">Simboli monitorati</div>
        <div class="tv-rows-subtitle">
            Le righe in arancione indicano simboli entro +/-10% dalla SMA 200W.
            Il pulsante Grafico apre il grafico weekly esistente.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

if st.button("Aggiorna dati", key="tv_refresh_data"):
    st.cache_data.clear()
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
# ORDINAMENTO RIGHE
# =========================

if sort_items is not None and len(symbols) > 1:
    st.markdown(
        """
        <div class="tv-sort-panel">
            <div class="tv-sort-title">Ordina simboli</div>
            <div class="tv-sort-subtitle">
                Trascina i simboli per modificare l'ordine della watchlist attiva.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    sorted_symbols = sort_items(
        symbols,
        direction="vertical",
        key="tv_sortable_rows_" + current
    )

    if sorted_symbols and sorted_symbols != symbols:
        st.session_state["tv_watchlists_data"]["watchlists"][current] = sorted_symbols
        salva_sessione_su_disco()
        st.rerun()

elif sort_items is None:
    st.info("Ordinamento righe non disponibile: verifica streamlit-sortables in requirements.txt.")


# =========================
# RENDER RIGHE
# =========================

symbols = st.session_state["tv_watchlists_data"]["watchlists"].get(current, [])

for symbol in list(symbols):
    metrics = get_stock_metrics(symbol)
    render_row(symbol, metrics)

    action_col_1, action_col_2, action_col_3 = st.columns([1.1, 1.1, 4.8])

    with action_col_1:
        if st.button("Grafico", key="tv_graph_" + symbol + "_" + current):
            st.session_state["ticker_selezionato"] = symbol
            st.switch_page("pages/grafico.py")

    with action_col_2:
        if st.button("Elimina", key="tv_delete_" + symbol + "_" + current):
            if symbol in st.session_state["tv_watchlists_data"]["watchlists"][current]:
                st.session_state["tv_watchlists_data"]["watchlists"][current].remove(symbol)
                salva_sessione_su_disco()
                st.cache_data.clear()
                st.rerun()

    st.markdown("")
