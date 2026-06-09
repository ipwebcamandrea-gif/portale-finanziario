import json
import re
from pathlib import Path
from html import escape

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
# CSS INLINE SPECIFICO
# =========================

st.markdown(
    """
    <style>
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

    div[class*="st-key-tv_zone_tab_"] .stButton > button:hover {
        border-color: rgba(255, 179, 71, 0.98);
        background:
            radial-gradient(circle at top right, rgba(255, 140, 0, 0.25), transparent 34%),
            linear-gradient(135deg, rgba(255, 140, 0, 0.22) 0%, rgba(255, 179, 71, 0.10) 100%);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.05),
            0 0 18px rgba(255, 140, 0, 0.42);
    }

    div[class*="st-key-tv_zone_tab_"][class*="st-key-tv_active_tab_"] .stButton > button {
        border-color: rgba(255, 179, 71, 1);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.07),
            0 0 0 1px rgba(255, 179, 71, 0.18),
            0 0 20px rgba(255, 140, 0, 0.42);
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

    .tv-zone-text-inline {
        color: #f5c542;
        font-weight: 950;
    }

    .tv-positive-inline {
        color: #00c853;
        font-weight: 950;
    }

    .tv-negative-inline {
        color: #ff1744;
        font-weight: 950;
    }

    .tv-neutral-inline {
        color: var(--text-muted);
        font-weight: 850;
    }

    div[data-testid="stHorizontalBlock"] .stButton > button {
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
        return "tv-neutral-inline"

    if value > 0:
        return "tv-positive-inline"

    if value < 0:
        return "tv-negative-inline"

    return "tv-neutral-inline"


def classe_zona_sma(value):
    if is_in_sma200_zone(value):
        return "tv-zone-text-inline"

    return classe_percentuale(value)


def cell_html(label, value, css_class="tv-cell-value"):
    return (
        f'<div class="tv-cell-label">{escape(label)}</div>'
        f'<div class="{css_class}">{escape(value)}</div>'
    )


def slug_safe(value):
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(value)).strip("_") or "item"


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
            [1.40, 1.00, 1.05, 1.18, 0.82, 1.25],
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
            action_col_1, action_col_2, action_col_3, action_col_4 = st.columns(4)

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
                if st.button(
                    "▲",
                    key="tv_up_" + symbol + "_" + current,
                    use_container_width=True,
                    help="Sposta simbolo in alto"
                ):
                    sposta_simbolo(current, symbol, -1)
                    st.rerun()

            with action_col_3:
                if st.button(
                    "▼",
                    key="tv_down_" + symbol + "_" + current,
                    use_container_width=True,
                    help="Sposta simbolo in basso"
                ):
                    sposta_simbolo(current, symbol, 1)
                    st.rerun()

            with action_col_4:
                if st.button(
                    "×",
                    key="tv_delete_" + symbol + "_" + current,
                    use_container_width=True,
                    help="Elimina simbolo dalla watchlist"
                ):
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


# =========================
# PAGE HEADER
# =========================

render_header()
render_persistence_note()


# =========================
# NAVIGAZIONE
# =========================

nav_col_1, nav_col_2 = st.columns([1.2, 4.8])

with nav_col_1:
    if st.button("Torna al Cockpit", key="tv_back_cockpit"):
        st.switch_page("pages/dashboard.py")


# =========================
# TABS WATCHLIST
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


# =========================
# AGGIUNGI SIMBOLO
# =========================

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
            Le azioni sono integrate nella stessa riga usando pulsanti Streamlit stabili.
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
# RENDER RIGHE STREAMLIT NATIVE
# =========================

for symbol in list(symbols):
    metrics = get_stock_metrics(symbol)
    render_row_streamlit(symbol, metrics, current)
