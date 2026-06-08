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


def identifica_mercato(ticker):
    ticker = ticker.upper().strip()

    if ticker.endswith(".MI"):
        return "Italia", "market-italy"

    if "." not in ticker:
        return "USA", "market-usa"

    return "Altro", "market-other"


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

    rendimento_1y = calcola_rendimento(hist, 252)

    return {
        "ticker": ticker,
        "prezzo": prezzo,
        "sma_200": sma_200,
        "distanza": distanza,
        "stato": stato,
        "rendimento_1y": rendimento_1y
    }


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
                "rendimento_1y": None
            })
        else:
            metriche["valido"] = True
            risultati.append(metriche)

    return risultati


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
    if stato == "Sopra SMA":
        return "status-positive"

    if stato == "Sotto SMA":
        return "status-negative"

    return "status-neutral"


def render_kpi_card(label, value, note):
    html = f"""
    <div class="watchlist-kpi-card">
        <div class="watchlist-kpi-label">{label}</div>
        <div class="watchlist-kpi-value">{value}</div>
        <div class="watchlist-kpi-note">{note}</div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def crea_label_ordinamento(item):
    ticker = item["ticker"]
    mercato_label, _ = identifica_mercato(ticker)

    if not item["valido"]:
        return f"⋮⋮  {ticker}  ·  {mercato_label}  ·  dati non disponibili"

    prezzo = formatta_prezzo(item["prezzo"])
    distanza = formatta_percentuale(item["distanza"])
    stato = item["stato"]

    return f"⋮⋮  {ticker}  ·  {mercato_label}  ·  {prezzo}  ·  {distanza}  ·  {stato}"


def render_ticker_card(item):
    ticker = item["ticker"]
    mercato_label, mercato_classe = identifica_mercato(ticker)

    if not item["valido"]:
        prezzo_str = "N/D"
        sma_str = "N/D"
        distanza_str = "N/D"
        rendimento_1y_str = "N/D"
        distanza_class = "neutral"
        rendimento_1y_class = "neutral"
        stato = "N/D"
        stato_class = "status-neutral"
    else:
        prezzo_str = formatta_prezzo(item["prezzo"])
        sma_str = formatta_prezzo(item["sma_200"])
        distanza_str = formatta_percentuale(item["distanza"])
        rendimento_1y_str = formatta_percentuale(item["rendimento_1y"])

        distanza_class = classe_valore(item["distanza"])
        rendimento_1y_class = classe_valore(item["rendimento_1y"])

        stato = item["stato"]
        stato_class = classe_stato(stato)

    html = f"""
    <div class="watchlist-card">
        <div class="watchlist-card-top">
            <div class="watchlist-card-left">
                <div class="drag-handle">⋮⋮</div>
                <div class="watchlist-symbol-block">
                    <div class="watchlist-ticker-symbol">{ticker}</div>
                    <div class="watchlist-ticker-subtitle">
                        Simbolo Yahoo Finance · Watchlist operativa
                    </div>
                </div>
            </div>

            <div class="watchlist-card-right">
                <span class="market-badge {mercato_classe}">{mercato_label}</span>
                <span class="status-pill {stato_class}">{stato}</span>
            </div>
        </div>

        <div class="watchlist-card-metrics">
            <div class="metric-box">
                <div class="metric-label">Prezzo</div>
                <div class="metric-value watchlist-price">{prezzo_str}</div>
            </div>

            <div class="metric-box">
                <div class="metric-label">SMA 200D</div>
                <div class="metric-value-small">{sma_str}</div>
            </div>

            <div class="metric-box">
                <div class="metric-label">Distanza</div>
                <div class="metric-value {distanza_class}">{distanza_str}</div>
            </div>

            <div class="metric-box">
                <div class="metric-label">Rendimento 1Y</div>
                <div class="metric-value {rendimento_1y_class}">{rendimento_1y_str}</div>
            </div>

            <div class="metric-box">
                <div class="metric-label">Mercato</div>
                <div class="metric-value-small">{mercato_label}</div>
            </div>
        </div>
    </div>
    """

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
            Card finanziarie ordinate, leggibili e ottimizzate anche per smartphone.
            Trascina le card per cambiare l'ordine, apri il grafico dal pulsante 📈
            o rimuovi un ticker con 🗑️.
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
# ORDINAMENTO CARD
# =========================

st.markdown(
    """
    <div class="watchlist-sort-panel">
        <div class="watchlist-sort-title">Ordina card Watchlist</div>
        <div class="watchlist-sort-subtitle">
            Trascina gli elementi qui sotto per cambiare l'ordine delle card.
            L'ordine viene salvato in watchlist.txt.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

if sort_items is not None:
    label_per_ticker = {}
    ticker_per_label = {}

    for item in risultati:
        ticker = item["ticker"]
        label = crea_label_ordinamento(item)

        label_per_ticker[ticker] = label
        ticker_per_label[label] = ticker

    lista_label_prima = [
        label_per_ticker[ticker]
        for ticker in st.session_state["lista_tickers"]
        if ticker in label_per_ticker
    ]

    lista_label_dopo = sort_items(
        lista_label_prima,
        direction="vertical",
        key="drag_drop_watchlist_cards"
    )

    if lista_label_dopo and lista_label_dopo != lista_label_prima:
        nuova_lista_ticker = [
            ticker_per_label[label]
            for label in lista_label_dopo
            if label in ticker_per_label
        ]

        st.session_state["lista_tickers"] = rimuovi_duplicati(nuova_lista_ticker)
        salva_ticker_su_file(st.session_state["lista_tickers"])
        st.success("Ordine watchlist aggiornato.")
        st.rerun()
else:
    st.info(
        "Ordinamento drag & drop non disponibile. "
        "Verifica che streamlit-sortables sia presente in requirements.txt."
    )


# =========================
# CARD OPERATIVE
# =========================

st.markdown(
    """
    <div class="watchlist-toolbar">
        <div class="watchlist-toolbar-title">Card operative</div>
        <div class="watchlist-toolbar-subtitle">
            Ogni card mostra prezzo, SMA 200D, distanza dalla media,
            stato tecnico e rendimento 1Y.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

risultati_per_ticker = {
    item["ticker"]: item
    for item in risultati
}

for ticker in st.session_state["lista_tickers"]:
    if ticker not in risultati_per_ticker:
        continue

    item = risultati_per_ticker[ticker]

    render_ticker_card(item)

    col_grafico, col_elimina, col_spazio = st.columns([1.2, 1.2, 3.6])

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
