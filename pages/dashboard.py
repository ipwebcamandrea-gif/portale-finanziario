import streamlit as st
import yfinance as yf
import pandas as pd
from pathlib import Path

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
# FUNZIONI WATCHLIST
# =========================

def carica_ticker_da_file():
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as file:
            return [
                line.strip().upper()
                for line in file.readlines()
                if line.strip()
            ]

    return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]


def salva_ticker_su_file(lista_ticker):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as file:
        for ticker in lista_ticker:
            file.write(f"{ticker}\n")


def rimuovi_duplicati(lista_ticker):
    lista_pulita = []

    for ticker in lista_ticker:
        ticker_pulito = ticker.strip().upper()

        if ticker_pulito and ticker_pulito not in lista_pulita:
            lista_pulita.append(ticker_pulito)

    return lista_pulita


# =========================
# FUNZIONI DATI FINANZIARI
# =========================

def valore_float(valore):
    if isinstance(valore, pd.Series):
        valore = valore.dropna()

        if valore.empty:
            return None

        valore = valore.iloc[0]

    if pd.isna(valore):
        return None

    return float(valore)


@st.cache_data(ttl=900, show_spinner=False)
def scarica_dati_ticker(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="2y", interval="1d")

    if hist is None or hist.empty:
        return pd.DataFrame()

    if "Close" not in hist.columns:
        return pd.DataFrame()

    hist = hist.dropna(subset=["Close"])

    return hist


def calcola_metriche(ticker):
    hist = scarica_dati_ticker(ticker)

    if hist.empty:
        return None

    prezzo = valore_float(hist["Close"].iloc[-1])

    if prezzo is None:
        return None

    sma_200 = valore_float(hist["Close"].rolling(200).mean().iloc[-1])

    if sma_200 is None:
        distanza = None
        stato = "N/D"
    else:
        distanza = ((prezzo - sma_200) / sma_200) * 100

        if distanza > 0:
            stato = "Sopra SMA"
        elif distanza < 0:
            stato = "Sotto SMA"
        else:
            stato = "In linea"

    rendimento_1m = calcola_rendimento(hist, 21)
    rendimento_6m = calcola_rendimento(hist, 126)
    rendimento_1y = calcola_rendimento(hist, 252)

    return {
        "ticker": ticker,
        "prezzo": prezzo,
        "sma_200": sma_200,
        "distanza": distanza,
        "stato": stato,
        "rendimento_1m": rendimento_1m,
        "rendimento_6m": rendimento_6m,
        "rendimento_1y": rendimento_1y
    }


def calcola_rendimento(hist, giorni):
    if hist is None or hist.empty:
        return None

    if len(hist) <= giorni:
        return None

    prezzo_attuale = valore_float(hist["Close"].iloc[-1])
    prezzo_passato = valore_float(hist["Close"].iloc[-giorni])

    if prezzo_attuale is None or prezzo_passato is None:
        return None

    if prezzo_passato == 0:
        return None

    return ((prezzo_attuale - prezzo_passato) / prezzo_passato) * 100


def costruisci_metriche_watchlist(lista_ticker):
    risultati = []

    for ticker in lista_ticker:
        metriche = calcola_metriche(ticker)

        if metriche is None:
            risultati.append({
                "ticker": ticker,
                "valido": False,
                "prezzo": None,
                "sma_200": None,
                "distanza": None,
                "stato": "N/D",
                "rendimento_1m": None,
                "rendimento_6m": None,
                "rendimento_1y": None
            })
        else:
            metriche["valido"] = True
            risultati.append(metriche)

    return risultati


# =========================
# FUNZIONI FORMATTAZIONE
# =========================

def formatta_prezzo(valore):
    if valore is None:
        return "N/D"

    return f"$ {valore:.2f}"


def formatta_percentuale(valore):
    if valore is None:
        return "N/D"

    return f"{valore:.2f} %"


def classe_valore(valore):
    if valore is None:
        return "neutral"

    if valore > 0:
        return "positive"

    if valore < 0:
        return "negative"

    return "neutral"


def classe_stato(stato):
    if stato == "Sopra SMA":
        return "status-positive"

    if stato == "Sotto SMA":
        return "status-negative"

    return "status-neutral"


def render_kpi_card(label, value, note):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# INIZIALIZZAZIONE SESSIONE
# =========================

if "lista_tickers" not in st.session_state:
    st.session_state["lista_tickers"] = rimuovi_duplicati(
        carica_ticker_da_file()
    )


# =========================
# HEADER
# =========================

st.markdown(
    """
    <div class="dashboard-header">
        <div class="main-title">Monitoraggio Globale Watchlist</div>
        <div class="subtitle">
            Dashboard V1.1 · Prezzi, SMA 200 giorni, stato tecnico e rendimenti principali.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# CONFIGURAZIONE WATCHLIST
# =========================

with st.expander("🛠️ Configura Watchlist", expanded=False):
    nuovo_ticker = st.text_input(
        "Aggiungi Ticker:",
        placeholder="Esempio: AAPL, NVDA, SWDA.MI",
        key="txt_add"
    ).upper().strip()

    if st.button("Aggiungi alla lista"):
        if not nuovo_ticker:
            st.warning("Inserisci un ticker valido.")

        elif nuovo_ticker in st.session_state["lista_tickers"]:
            st.warning(f"{nuovo_ticker} è già presente nella watchlist.")

        else:
            st.session_state["lista_tickers"].append(nuovo_ticker)
            st.session_state["lista_tickers"] = rimuovi_duplicati(
                st.session_state["lista_tickers"]
            )
            salva_ticker_su_file(st.session_state["lista_tickers"])
            st.success(f"{nuovo_ticker} aggiunto alla watchlist.")
            st.rerun()

    st.markdown("#### Ordina ticker")

    lista_prima = list(st.session_state["lista_tickers"])

    if sort_items is not None:
        lista_dopo = sort_items(
            lista_prima,
            direction="vertical",
            key="drag_drop"
        )

        if lista_dopo and lista_dopo != lista_prima:
            st.session_state["lista_tickers"] = rimuovi_duplicati(lista_dopo)
            salva_ticker_su_file(st.session_state["lista_tickers"])
            st.rerun()
    else:
        st.info(
            "Ordinamento drag & drop non disponibile. "
            "Verifica che streamlit-sortables sia presente in requirements.txt."
        )


# =========================
# NAVIGAZIONE RAPIDA
# =========================

col_nav_1, col_nav_2, col_nav_3 = st.columns([1, 1, 3])

with col_nav_1:
    if st.button("📊 Watchlist"):
        st.switch_page("pages/watchlist.py")

with col_nav_2:
    if st.button("💼 Portafoglio"):
        st.switch_page("pages/portafoglio.py")


# =========================
# DATI DASHBOARD
# =========================

st.markdown("---")

if not st.session_state["lista_tickers"]:
    st.info("La watchlist è vuota. Aggiungi almeno un ticker.")
    st.stop()

with st.spinner("Aggiornamento dati finanziari in corso..."):
    risultati = costruisci_metriche_watchlist(
        st.session_state["lista_tickers"]
    )

ticker_totali = len(risultati)
ticker_validi = len([item for item in risultati if item["valido"]])
ticker_non_validi = ticker_totali - ticker_validi

sopra_sma = len([
    item for item in risultati
    if item["valido"] and item["stato"] == "Sopra SMA"
])

sotto_sma = len([
    item for item in risultati
    if item["valido"] and item["stato"] == "Sotto SMA"
])

validi_con_distanza = [
    item for item in risultati
    if item["valido"] and item["distanza"] is not None
]

migliore = None
peggiore = None

if validi_con_distanza:
    migliore = max(validi_con_distanza, key=lambda item: item["distanza"])
    peggiore = min(validi_con_distanza, key=lambda item: item["distanza"])


# =========================
# KPI CARDS
# =========================

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

with kpi_1:
    render_kpi_card(
        "Ticker totali",
        ticker_totali,
        f"{ticker_validi} validi · {ticker_non_validi} non disponibili"
    )

with kpi_2:
    render_kpi_card(
        "Sopra SMA 200D",
        sopra_sma,
        f"{sotto_sma} sotto SMA 200D"
    )

with kpi_3:
    if migliore is not None:
        render_kpi_card(
            "Migliore distanza",
            migliore["ticker"],
            formatta_percentuale(migliore["distanza"])
        )
    else:
        render_kpi_card(
            "Migliore distanza",
            "N/D",
            "Dati non disponibili"
        )

with kpi_4:
    if peggiore is not None:
        render_kpi_card(
            "Peggiore distanza",
            peggiore["ticker"],
            formatta_percentuale(peggiore["distanza"])
        )
    else:
        render_kpi_card(
            "Peggiore distanza",
            "N/D",
            "Dati non disponibili"
        )


# =========================
# TABELLA WATCHLIST
# =========================

st.markdown(
    """
    <div class="dashboard-toolbar">
        <div class="toolbar-title">Watchlist operativa</div>
        <div class="toolbar-subtitle">
            Clicca su 📈 per aprire il grafico dettagliato del titolo.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

header = st.columns([0.8, 1.5, 1.4, 1.4, 1.4, 1.4, 1.2, 0.8])

header[0].markdown('<div class="table-header">Grafico</div>', unsafe_allow_html=True)
header[1].markdown('<div class="table-header">Ticker</div>', unsafe_allow_html=True)
header[2].markdown('<div class="table-header">Prezzo</div>', unsafe_allow_html=True)
header[3].markdown('<div class="table-header">SMA 200D</div>', unsafe_allow_html=True)
header[4].markdown('<div class="table-header">Distanza</div>', unsafe_allow_html=True)
header[5].markdown('<div class="table-header">Stato</div>', unsafe_allow_html=True)
header[6].markdown('<div class="table-header">1Y</div>', unsafe_allow_html=True)
header[7].markdown('<div class="table-header">Elimina</div>', unsafe_allow_html=True)

st.divider()


for item in risultati:
    ticker = item["ticker"]
    cols = st.columns([0.8, 1.5, 1.4, 1.4, 1.4, 1.4, 1.2, 0.8])

    if cols[0].button("📈", key=f"graf_{ticker}"):
        st.session_state["ticker_selezionato"] = ticker
        st.switch_page("pages/grafico.py")

    cols[1].markdown(
        f'<div class="watchlist-ticker">{ticker}</div>',
        unsafe_allow_html=True
    )

    if not item["valido"]:
        cols[2].warning("N/D")
        cols[3].write("N/D")
        cols[4].write("N/D")
        cols[5].markdown(
            '<span class="status-pill status-neutral">N/D</span>',
            unsafe_allow_html=True
        )
        cols[6].write("N/D")

    else:
        prezzo_str = formatta_prezzo(item["prezzo"])
        sma_str = formatta_prezzo(item["sma_200"])
        distanza_str = formatta_percentuale(item["distanza"])
        rendimento_1y_str = formatta_percentuale(item["rendimento_1y"])

        distanza_class = classe_valore(item["distanza"])
        rendimento_1y_class = classe_valore(item["rendimento_1y"])
        stato_class = classe_stato(item["stato"])

        cols[2].markdown(
            f'<div class="watchlist-price">{prezzo_str}</div>',
            unsafe_allow_html=True
        )

        cols[3].markdown(
            f'<div class="watchlist-muted">{sma_str}</div>',
            unsafe_allow_html=True
        )

        cols[4].markdown(
            f'<span class="{distanza_class}">{distanza_str}</span>',
            unsafe_allow_html=True
        )

        cols[5].markdown(
            f'<span class="status-pill {stato_class}">{item["stato"]}</span>',
            unsafe_allow_html=True
        )

        cols[6].markdown(
            f'<span class="{rendimento_1y_class}">{rendimento_1y_str}</span>',
            unsafe_allow_html=True
        )

    if cols[7].button("🗑️", key=f"del_{ticker}"):
        st.session_state["lista_tickers"].remove(ticker)
        salva_ticker_su_file(st.session_state["lista_tickers"])
        st.rerun()

    st.divider()
