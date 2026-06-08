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
        return {
            "ticker": ticker,
            "prezzo": prezzo,
            "sma_200": None,
            "distanza": None
        }

    distanza = ((prezzo - sma_200) / sma_200) * 100

    return {
        "ticker": ticker,
        "prezzo": prezzo,
        "sma_200": sma_200,
        "distanza": distanza
    }


def formatta_prezzo(valore):
    if valore is None:
        return "N/D"

    return f"$ {valore:.2f}"


def formatta_percentuale(valore):
    if valore is None:
        return "N/D"

    return f"{valore:.2f} %"


def classe_distanza(valore):
    if valore is None:
        return "neutral"

    if valore > 0:
        return "positive"

    if valore < 0:
        return "negative"

    return "neutral"


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
    '<div class="main-title">Monitoraggio Globale Watchlist</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Prezzi, media mobile a 200 giorni e distanza percentuale dalla media.</div>',
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

        if lista_dopo != lista_prima:
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
# TABELLA WATCHLIST
# =========================

st.markdown("---")

if not st.session_state["lista_tickers"]:
    st.info("La watchlist è vuota. Aggiungi almeno un ticker.")
    st.stop()


header = st.columns([1, 2, 2, 2, 2, 1])

with header[0]:
    st.markdown("**Grafico**")

with header[1]:
    st.markdown("**Ticker**")

with header[2]:
    st.markdown("**Prezzo**")

with header[3]:
    st.markdown("**SMA 200D**")

with header[4]:
    st.markdown("**Distanza**")

with header[5]:
    st.markdown("**Elimina**")

st.divider()


for ticker in list(st.session_state["lista_tickers"]):
    try:
        metriche = calcola_metriche(ticker)

        cols = st.columns([1, 2, 2, 2, 2, 1])

        if metriche is None:
            with cols[0]:
                st.write("")

            with cols[1]:
                st.markdown(f"**{ticker}**")

            with cols[2]:
                st.warning("N/D")

            with cols[3]:
                st.write("N/D")

            with cols[4]:
                st.write("N/D")

            with cols[5]:
                if st.button("🗑️", key=f"del_{ticker}"):
                    st.session_state["lista_tickers"].remove(ticker)
                    salva_ticker_su_file(st.session_state["lista_tickers"])
                    st.rerun()

            st.divider()
            continue

        prezzo = metriche["prezzo"]
        sma_200 = metriche["sma_200"]
        distanza = metriche["distanza"]

        prezzo_str = formatta_prezzo(prezzo)
        sma_str = formatta_prezzo(sma_200)
        distanza_str = formatta_percentuale(distanza)
        distanza_class = classe_distanza(distanza)

        with cols[0]:
            if st.button("📈", key=f"graf_{ticker}"):
                st.session_state["ticker_selezionato"] = ticker
                st.switch_page("pages/grafico.py")

        with cols[1]:
            st.markdown(f"**{ticker}**")

        with cols[2]:
            st.markdown(prezzo_str)

        with cols[3]:
            st.markdown(sma_str)

        with cols[4]:
            st.markdown(
                f'<span class="{distanza_class}">{distanza_str}</span>',
                unsafe_allow_html=True
            )

        with cols[5]:
            if st.button("🗑️", key=f"del_{ticker}"):
                st.session_state["lista_tickers"].remove(ticker)
                salva_ticker_su_file(st.session_state["lista_tickers"])
                st.rerun()

        st.divider()

    except Exception as errore:
        st.warning(f"Errore su {ticker}: {errore}")
        continue
