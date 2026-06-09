import json
from pathlib import Path
from html import escape
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st
import yfinance as yf


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
# CSS MINIMO PER AZIONI INLINE
# =========================

st.markdown(
    """
    <style>
    .tv-row-grid {
        grid-template-columns: 1.40fr 1.00fr 1.05fr 1.18fr 0.82fr 1.25fr;
    }

    .tv-actions-inline {
        display: flex;
        align-items: center;
        gap: 0.42rem;
        justify-content: flex-start;
    }

    .tv-action-link {
        width: 34px;
        height: 30px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 9px;
        border: 1px solid rgba(48, 54, 61, 0.95);
        background: linear-gradient(180deg, #202733 0%, #151b24 100%);
        color: #e6edf3 !important;
        text-decoration: none !important;
        font-size: 0.86rem;
        font-weight: 950;
        line-height: 1;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }

    .tv-action-link:hover {
        border-color: rgba(0, 176, 255, 0.70);
        background: linear-gradient(180deg, #2a3442 0%, #1a222d 100%);
        color: #ffffff !important;
        transform: translateY(-1px);
    }

    .tv-action-link-danger:hover {
        border-color: rgba(239, 83, 80, 0.90);
        background: linear-gradient(180deg, rgba(239,83,80,0.30) 0%, rgba(90,25,25,0.35) 100%);
    }

    .tv-action-chart svg {
        width: 17px;
        height: 17px;
        display: block;
    }

    .tv-action-chart path,
    .tv-action-chart polyline {
        stroke: #00c853;
    }

    @media (max-width: 1100px) {
        .tv-row-grid {
            grid-template-columns: 1.35fr 1fr 1fr;
        }
    }

    @media (max-width: 760px) {
        .tv-row-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


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

def copia_default_data():
    return json.loads(json.dumps(DEFAULT_DATA))


def normalizza_dati_watchlists(data):
    if not isinstance(data, dict):
        return copia_default_data()

    if "watchlists" not in data or not isinstance(data["watchlists"], dict):
        if all(isinstance(value, list) for value in data.values()):
            data = {
                "version": 1,
                "active_watchlist": list(data.keys())[0] if data else "Default",
                "watchlists": data
            }
        else:
            return copia_default_data()

    if "version" not in data:
        data["version"] = 1

    watchlists = data.get("watchlists", {})

    if not watchlists:
        watchlists = {"Default": []}
        data["watchlists"] = watchlists

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
        salva_watchlists_su_json(copia_default_data())
        return copia_default_data()

    try:
        with open(WATCHLISTS_JSON, "r", encoding="utf-8") as file:
            data = json.load(file)

        return normalizza_dati_watchlists(data)

    except Exception:
        return copia_default_data()


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


# =========================
# QUERY PARAM ACTIONS
# =========================

def query_value(name):
    value = st.query_params.get(name, None)

    if isinstance(value, list):
        return value[0] if value else None

    return value


def clear_query_params():
    try:
        st.query_params.clear()
    except Exception:
        pass


def gestisci_azioni_da_query():
    action = query_value("tv_action")
    symbol = query_value("tv_symbol")
    list_name = query_value("tv_list")

    if not action or not symbol or not list_name:
        return

    data = st.session_state.get("tv_watchlists_data")

    if not data:
        clear_query_params()
        return

    watchlists = data.get("watchlists", {})

    if list_name not in watchlists:
        clear_query_params()
        st.rerun()

    if action == "graph":
        st.session_state["ticker_selezionato"] = symbol
        clear_query_params()
        st.switch_page("pages/grafico.py")

    if action == "up":
        sposta_simbolo(list_name, symbol, -1)
        clear_query_params()
        st.rerun()

    if action == "down":
        sposta_simbolo(list_name, symbol, 1)
        clear_query_params()
        st.rerun()

    if action == "delete":
        if symbol in watchlists.get(list_name, []):
            watchlists[list_name].remove(symbol)
            salva_sessione_su_disco()
            st.cache_data.clear()
        clear_query_params()
        st.rerun()


# =========================
# HELPERS DATI YFINANCE
# =========================

def normalizza_dataframe_yfinance(data):
    if isinstance(data.columns, pd.MultiIndex):
        livello_0 = list(data.columns.get_level_values(0))
        livello_1 = list(data.columns.get_level_values(1))

        if "Close" in livello_0:
            data.columns = data.columns.get_level_values(0)
        elif "Close" in livello_1:
            data.columns = data.columns.get_level_values(1)

    return data


def valore_float_sicuro(value):
    if isinstance(value, pd.Series):
        value = value.dropna()
        if value.empty:
            return None
        value = value.iloc[0]

    if value is None or pd.isna(value):
        return None

    return float(value)


# =========================
# METRICHE FINANZIARIE
# =========================

@st.cache_data(ttl=900, show_spinner=False)
def get_stock_metrics(symbol):
    try:
        last_price = None
        previous_close = None
        currency = ""

        try:
            intraday = yf.download(
                symbol,
                period="5d",
                interval="15m",
                auto_adjust=False,
                progress=False,
                threads=False
            )

            if intraday is not None and not intraday.empty:
                intraday = normalizza_dataframe_yfinance(intraday)

                if "Close" in intraday.columns:
                    intraday = intraday.dropna(subset=["Close"])

                    if not intraday.empty:
                        last_price = valore_float_sicuro(intraday["Close"].iloc[-1])

        except Exception:
            pass

        try:
            daily = yf.download(
                symbol,
                period="10d",
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=False
            )

            if daily is not None and not daily.empty:
                daily = normalizza_dataframe_yfinance(daily)

                if "Close" in daily.columns:
                    daily = daily.dropna(subset=["Close"])

                    if len(daily) >= 2:
                        previous_close = valore_float_sicuro(daily["Close"].iloc[-2])
                    elif len(daily) == 1:
                        previous_close = valore_float_sicuro(daily["Close"].iloc[-1])

        except Exception:
            pass

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info

            def fast_value(*keys):
                for key in keys:
                    try:
                        value = info.get(key, None)
                    except Exception:
                        try:
                            value = info[key]
                        except Exception:
                            value = None

                    if value is not None:
                        return value

                return None

            if last_price is None:
                last_price = valore_float_sicuro(
                    fast_value(
                        "last_price",
                        "lastPrice",
                        "regularMarketPrice"
                    )
                )

            if previous_close is None:
                previous_close = valore_float_sicuro(
                    fast_value(
                        "previous_close",
                        "previousClose",
                        "regularMarketPreviousClose"
                    )
                )

            currency = fast_value("currency") or ""

        except Exception:
            pass

        sma200 = None
        dist_pct = None

        try:
            weekly = yf.download(
                symbol,
                period="10y",
                interval="1wk",
                auto_adjust=False,
                progress=False,
                threads=False
            )

            if weekly is not None and not weekly.empty:
                weekly = normalizza_dataframe_yfinance(weekly)

                if "Close" in weekly.columns:
                    weekly = weekly.dropna(subset=["Close"])

                    if last_price is None and not weekly.empty:
                        last_price = valore_float_sicuro(weekly["Close"].iloc[-1])

                    if len(weekly) >= 200:
                        sma200 = valore_float_sicuro(
                            weekly["Close"].rolling(200).mean().iloc[-1]
                        )

                        if sma200 is not None and sma200 != 0 and last_price is not None:
                            dist_pct = ((last_price - sma200) / sma200) * 100

        except Exception:
            pass

        daily_change_pct = None

        if last_price is not None and previous_close is not None and previous_close != 0:
            daily_change_pct = ((last_price - previous_close) / previous_close) * 100

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


def action_url(action, symbol, list_name):
    return (
        "?tv_action=" + quote_plus(action)
        + "&tv_symbol=" + quote_plus(symbol)
        + "&tv_list=" + quote_plus(list_name)
    )


def chart_svg():
    return (
        '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">'
        '<path d="M4 19.5H20" stroke-width="1.8" stroke-linecap="round"/>'
        '<path d="M5 16L9 12L12 14.5L18.5 7.5" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M15.5 7.5H18.5V10.5" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>'
    )


def render_action_links(symbol, current):
    symbol_safe = escape(symbol)
    current_safe = escape(current)

    return (
        '<div class="tv-actions-inline">'
        f'<a class="tv-action-link tv-action-chart" href="{action_url("graph", symbol, current)}" title="Apri grafico tecnico weekly per {symbol_safe}">{chart_svg()}</a>'
        f'<a class="tv-action-link" href="{action_url("up", symbol, current)}" title="Sposta {symbol_safe} in alto">▲</a>'
        f'<a class="tv-action-link" href="{action_url("down", symbol, current)}" title="Sposta {symbol_safe} in basso">▼</a>'
        f'<a class="tv-action-link tv-action-link-danger" href="{action_url("delete", symbol, current)}" title="Elimina {symbol_safe} da {current_safe}">×</a>'
        '</div>'
    )


# =========================
# RENDER HTML
# =========================

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
            <div class="tv-active-list-name">{escape(current)}</div>
            <div class="tv-active-list-note">
                {len(symbols)} simboli monitorati · Yahoo Finance 15m/delayed · SMA 200W su timeframe weekly.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_row(symbol, metrics, current):
    dist_pct = metrics["dist_pct"]
    daily_pct = metrics["daily_change_pct"]
    sma200w = metrics.get("sma200w")
    row_class = "tv-row tv-row-zone" if is_in_sma200_zone(dist_pct) else "tv-row"

    prezzo = formatta_prezzo(metrics["last_price"], metrics["currency"])
    sma200w_testo = formatta_prezzo(sma200w, metrics["currency"])
    distanza = formatta_percentuale(dist_pct)
    daily = formatta_percentuale(daily_pct)

    daily_class = classe_percentuale(daily_pct)
    dist_class = classe_zona_sma(dist_pct)

    zone_note = "Zona SMA200W" if is_in_sma200_zone(dist_pct) else "Monitoraggio"
    actions_html = render_action_links(symbol, current)

    html = (
        f'<div class="{row_class}">'
        '<div class="tv-row-grid">'
        '<div class="tv-symbol-block">'
        f'<div class="tv-symbol">{escape(symbol)}</div>'
        f'<div class="tv-symbol-note">{zone_note}</div>'
        '</div>'
        '<div>'
        '<div class="tv-metric-label">Prezzo</div>'
        f'<div class="tv-metric-value tv-price">{escape(prezzo)}</div>'
        '</div>'
        '<div>'
        '<div class="tv-metric-label">SMA 200W</div>'
        f'<div class="tv-metric-value tv-price">{escape(sma200w_testo)}</div>'
        '</div>'
        '<div>'
        '<div class="tv-metric-label">Distanza SMA200W</div>'
        f'<div class="tv-metric-value {dist_class}">{escape(distanza)}</div>'
        '</div>'
        '<div>'
        '<div class="tv-metric-label">Daily</div>'
        f'<div class="tv-metric-value {daily_class}">{escape(daily)}</div>'
        '</div>'
        '<div>'
        '<div class="tv-metric-label">Azioni</div>'
        f'{actions_html}'
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

# Gestione click sulle azioni inline nella card
# Deve avvenire dopo l'inizializzazione della sessione.
gestisci_azioni_da_query()


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
            Seleziona una lista, crea nuove tab o sposta la tab attiva con i pulsanti sinistra/destra.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

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

move_tab_col_1, move_tab_col_2, move_tab_col_3 = st.columns([0.55, 0.55, 5.9])

with move_tab_col_1:
    if st.button(
        "◀",
        key="tv_move_tab_left",
        use_container_width=True,
        help="Sposta la watchlist attiva a sinistra"
    ):
        sposta_watchlist(st.session_state["tv_current_list"], -1)
        st.rerun()

with move_tab_col_2:
    if st.button(
        "▶",
        key="tv_move_tab_right",
        use_container_width=True,
        help="Sposta la watchlist attiva a destra"
    ):
        sposta_watchlist(st.session_state["tv_current_list"], 1)
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
            Prezzo da Yahoo Finance intraday 15m/delayed. SMA 200W calcolata su weekly 10 anni.
            Le azioni rapide sono integrate nella card di ogni simbolo.
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
# RENDER RIGHE
# =========================

for symbol in list(symbols):
    metrics = get_stock_metrics(symbol)
    render_row(symbol, metrics, current)
