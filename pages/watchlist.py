import streamlit as st
import yfinance as yf
import pandas as pd
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
WATCHLIST_FILE = ROOT_DIR / "watchlist.txt"

GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
WATCHLIST_CSS = ROOT_DIR / "css" / "watchlist.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(
                f"<style>{file.read()}</style>",
                unsafe_allow_html=True
            )


local_css(GLOBAL_CSS)
local_css(WATCHLIST_CSS)


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


def sposta_ticker(lista_ticker, ticker, direzione):
    lista_nuova = list(lista_ticker)

    if ticker not in lista_nuova:
        return lista_nuova

    indice = lista_nuova.index(ticker)
    nuovo_indice = indice + direzione

    if nuovo_indice < 0 or nuovo_indice >= len(lista_nuova):
        return lista_nuova

    lista_nuova[indice], lista_nuova[nuovo_indice] = (
        lista_nuova[nuovo_indice],
        lista_nuova[indice]
    )

    return lista_nuova


def identifica_mercato(ticker):
    ticker = ticker.upper().strip()

    if ticker.endswith(".MI"):
        return "Italia", "market-italy"

    if "." not in ticker:
        return "USA", "market-usa"

    return "Altro", "market-other"


# =========================
# FUNZIONI DATI FINANZIARI WEEKLY
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
def scarica_dati_weekly_batch(lista_ticker_tuple):
    """
    Scarica dati weekly a 10 anni in batch.
    Serve per calcolare SMA 200W in modo più coerente con grafici tipo TradingView.
    """
    lista_ticker = list(lista_ticker_tuple)

    if not lista_ticker:
        return {}, None

    try:
        data = yf.download(
            tickers=lista_ticker,
            period="10y",
            interval="1wk",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=False
        )

    except Exception as errore:
        return {}, str(errore)

    dati_per_ticker = {}

    if data is None or data.empty:
        return dati_per_ticker, None

    # Caso ticker singolo
    if len(lista_ticker) == 1:
        ticker = lista_ticker[0]
        df = data.copy()

        if isinstance(df.columns, pd.MultiIndex):
            try:
                if ticker in df.columns.get_level_values(0):
                    df = df[ticker].copy()
                else:
                    df.columns = df.columns.get_level_values(-1)
            except Exception:
                df.columns = df.columns.get_level_values(-1)

        if "Close" in df.columns:
            df = df.dropna(subset=["Close"])
            dati_per_ticker[ticker] = df

        return dati_per_ticker, None

    # Caso più ticker
    if isinstance(data.columns, pd.MultiIndex):
        livello_zero = list(data.columns.get_level_values(0))

        for ticker in lista_ticker:
            try:
                if ticker in livello_zero:
                    df = data[ticker].copy()

                    if "Close" in df.columns:
                        df = df.dropna(subset=["Close"])
                        dati_per_ticker[ticker] = df
            except Exception:
                continue

    return dati_per_ticker, None


def calcola_rendimento_weekly(hist, settimane):
    if hist is None or hist.empty:
        return None

    if len(hist) <= settimane:
        return None

    prezzo_attuale = valore_float(hist["Close"].iloc[-1])
    prezzo_passato = valore_float(hist["Close"].iloc[-settimane])

    if prezzo_attuale is None or prezzo_passato is None:
        return None

    if prezzo_passato == 0:
        return None

    return ((prezzo_attuale - prezzo_passato) / prezzo_passato) * 100


def calcola_metriche_da_storico(ticker, hist):
    if hist is None or hist.empty:
        return None

    if "Close" not in hist.columns:
        return None

    prezzo = valore_float(hist["Close"].iloc[-1])

    if prezzo is None:
        return None

    sma_200w = valore_float(hist["Close"].rolling(200).mean().iloc[-1])

    if sma_200w is None:
        distanza = None
        stato = "N/D"
    else:
        distanza = ((prezzo - sma_200w) / sma_200w) * 100

        if distanza > 0:
            stato = "Sopra SMA 200W"
        elif distanza < 0:
            stato = "Sotto SMA 200W"
        else:
            stato = "In linea SMA 200W"

    rendimento_52w = calcola_rendimento_weekly(hist, 52)

    return {
        "ticker": ticker,
        "prezzo": prezzo,
        "sma_200w": sma_200w,
        "distanza": distanza,
        "stato": stato,
        "rendimento_52w": rendimento_52w
    }


def costruisci_metriche_watchlist(lista_ticker):
    dati_per_ticker, errore_download = scarica_dati_weekly_batch(
        tuple(lista_ticker)
    )

    risultati = []

    for ticker in lista_ticker:
        hist = dati_per_ticker.get(ticker, pd.DataFrame())
        metriche = calcola_metriche_da_storico(ticker, hist)

        if metriche is None:
            risultati.append({
                "ticker": ticker,
                "valido": False,
                "prezzo": None,
                "sma_200w": None,
                "distanza": None,
                "stato": "N/D",
                "rendimento_52w": None
            })
        else:
            metriche["valido"] = True
            risultati.append(metriche)

    return risultati, errore_download


# =========================
# FORMATTAZIONE
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
    if stato == "Sopra SMA 200W":
        return "status-positive"

    if stato == "Sotto SMA 200W":
        return "status-negative"

    return "status-neutral"


def classe_card(item):
    if not item["valido"]:
        return ""

    if item["stato"] == "Sotto SMA 200W":
        return "watchlist-card-warning"

    return ""


def render_kpi_card(label, value, note):
    html = (
        '<div class="watchlist-kpi-card">'
        f'<div class="watchlist-kpi-label">{label}</div>'
        f'<div class="watchlist-kpi-value">{value}</div>'
        f'<div class="watchlist-kpi-note">{note}</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


def render_ticker_card(item):
    ticker = item["ticker"]
    mercato_label, mercato_classe = identifica_mercato(ticker)
    card_extra_class = classe_card(item)

    if not item["valido"]:
        prezzo_str = "N/D"
        sma_str = "N/D"
        distanza_str = "N/D"
        rendimento_52w_str = "N/D"
        distanza_class = "neutral"
        rendimento_52w_class = "neutral"
        stato = "N/D"
        stato_class = "status-neutral"
    else:
        prezzo_str = formatta_prezzo(item["prezzo"])
        sma_str = formatta_prezzo(item["sma_200w"])
        distanza_str = formatta_percentuale(item["distanza"])
        rendimento_52w_str = formatta_percentuale(item["rendimento_52w"])

        distanza_class = classe_valore(item["distanza"])
        rendimento_52w_class = classe_valore(item["rendimento_52w"])

        stato = item["stato"]
        stato_class = classe_stato(stato)

    html = (
        f'<div class="watchlist-card {card_extra_class}">'
            '<div class="watchlist-card-top">'
                '<div class="watchlist-card-left">'
                    '<div class="drag-handle">⋮⋮</div>'
                    '<div class="watchlist-symbol-block">'
                        f'<div class="watchlist-ticker-symbol">{ticker}</div>'
                        '<div class="watchlist-ticker-subtitle">'
                            'Timeframe weekly 10 anni · Logica SMA 200W'
                        '</div>'
                    '</div>'
                '</div>'
                '<div class="watchlist-card-right">'
                    f'<span class="market-badge {mercato_classe}">{mercato_label}</span>'
                    f'<span class="status-pill {stato_class}">{stato}</span>'
                '</div>'
            '</div>'
            '<div class="watchlist-card-metrics">'
                '<div class="metric-box">'
                    '<div class="metric-label">Prezzo</div>'
                    f'<div class="metric-value watchlist-price">{prezzo_str}</div>'
                '</div>'
                '<div class="metric-box">'
                    '<div class="metric-label">SMA 200W</div>'
                    f'<div class="metric-value-small">{sma_str}</div>'
                '</div>'
                '<div class="metric-box">'
                    '<div class="metric-label">Distanza SMA 200W</div>'
                    f'<div class="metric-value {distanza_class}">{distanza_str}</div>'
                '</div>'
                '<div class="metric-box">'
                    '<div class="metric-label">Rendimento 52W</div>'
                    f'<div class="metric-value {rendimento_52w_class}">{rendimento_52w_str}</div>'
                '</div>'
                '<div class="metric-box">'
                    '<div class="metric-label">Mercato</div>'
                    f'<div class="metric-value-small">{mercato_label}</div>'
                '</div>'
            '</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


# =========================
# SESSIONE
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
    <div class="watchlist-header">
        <div class="watchlist-title">Watchlist Operativa</div>
        <div class="watchlist-subtitle">
            Monitoraggio weekly a 10 anni con prezzo, SMA 200W, distanza dalla media,
            stato tecnico e rendimento a 52 settimane. Le card arancioni indicano
            titoli sotto la SMA 200W.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# NAVIGAZIONE
# =========================

st.markdown(
    """
    <div class="watchlist-topbar">
        <div class="watchlist-topbar-title">Navigazione</div>
        <div class="watchlist-topbar-text">
            Torna al Cockpit per aprire Portafoglio o Logout.
            Il grafico si apre solo dalla card ticker.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

col_nav_1, col_nav_2 = st.columns([1.2, 4.8])

with col_nav_1:
    if st.button("⬅️ Cockpit"):
        st.switch_page("pages/dashboard.py")


# =========================
# CONFIGURAZIONE WATCHLIST
# =========================

with st.expander("🛠️ Configura Watchlist", expanded=False):
    st.markdown(
        """
        <div class="watchlist-config-panel">
            <div class="watchlist-config-title">Gestione ticker</div>
            <div class="watchlist-config-subtitle">
                Aggiungi nuovi simboli Yahoo Finance.
                La lista viene salvata in watchlist.txt.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    nuovo_ticker = st.text_input(
        "Aggiungi Ticker:",
        placeholder="Esempio: AAPL, NVDA, SWDA.MI",
        key="txt_add_watchlist"
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


# =========================
# DATI WATCHLIST
# =========================

st.markdown("---")

if not st.session_state["lista_tickers"]:
    st.markdown(
        """
        <div class="watchlist-empty">
            La watchlist è vuota. Aggiungi almeno un ticker per iniziare.
        </div>
        """,
        unsafe_allow_html=True
    )
    st.stop()

with st.spinner("Aggiornamento dati weekly a 10 anni in corso..."):
    risultati, errore_download = costruisci_metriche_watchlist(
        st.session_state["lista_tickers"]
    )

if errore_download:
    st.warning(
        "Yahoo Finance/YFinance ha limitato temporaneamente le richieste. "
        "La pagina resta attiva, ma alcuni dati possono apparire come N/D. "
        "Riprova tra qualche minuto."
    )

ticker_totali = len(risultati)
ticker_validi = len([item for item in risultati if item["valido"]])
ticker_non_validi = ticker_totali - ticker_validi

sopra_sma = len([
    item for item in risultati
    if item["valido"] and item["stato"] == "Sopra SMA 200W"
])

sotto_sma = len([
    item for item in risultati
    if item["valido"] and item["stato"] == "Sotto SMA 200W"
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
# KPI
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
        "Sopra SMA 200W",
        sopra_sma,
        f"{sotto_sma} sotto SMA 200W"
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
# CARD OPERATIVE
# =========================

st.markdown(
    """
    <div class="watchlist-toolbar">
        <div class="watchlist-toolbar-title">Card operative weekly</div>
        <div class="watchlist-toolbar-subtitle">
            Ogni card mostra prezzo, SMA 200W, distanza dalla SMA 200W,
            stato tecnico e rendimento 52W. Le card arancioni sono sotto SMA 200W.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

risultati_per_ticker = {
    item["ticker"]: item
    for item in risultati
}

for ticker in list(st.session_state["lista_tickers"]):
    if ticker not in risultati_per_ticker:
        continue

    item = risultati_per_ticker[ticker]

    render_ticker_card(item)

    col_su, col_giu, col_grafico, col_elimina, col_spazio = st.columns(
        [0.8, 0.8, 1.2, 1.2, 3.2]
    )

    with col_su:
        if st.button("⬆️", key=f"up_{ticker}"):
            st.session_state["lista_tickers"] = sposta_ticker(
                st.session_state["lista_tickers"],
                ticker,
                -1
            )
            salva_ticker_su_file(st.session_state["lista_tickers"])
            st.rerun()

    with col_giu:
        if st.button("⬇️", key=f"down_{ticker}"):
            st.session_state["lista_tickers"] = sposta_ticker(
                st.session_state["lista_tickers"],
                ticker,
                1
            )
            salva_ticker_su_file(st.session_state["lista_tickers"])
            st.rerun()

    with col_grafico:
        if st.button("📈 Grafico", key=f"graf_{ticker}"):
            st.session_state["ticker_selezionato"] = ticker
            st.switch_page("pages/grafico.py")

    with col_elimina:
        if st.button("🗑️ Elimina", key=f"del_{ticker}"):
            st.session_state["lista_tickers"].remove(ticker)
            salva_ticker_su_file(st.session_state["lista_tickers"])
            st.rerun()

    st.markdown("")
