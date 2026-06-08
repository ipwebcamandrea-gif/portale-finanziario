import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path


# =========================
# PROTEZIONE LOGIN
# =========================

if not st.session_state.get("authenticated", False):
    st.error("Accesso negato.")

    if st.button("Torna al Login"):
        st.switch_page("main.py")

    st.stop()


# =========================
# CONFIGURAZIONE FILE / CSS
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent
GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
GRAFICO_CSS = ROOT_DIR / "css" / "grafico.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(
                f"<style>{file.read()}</style>",
                unsafe_allow_html=True
            )


local_css(GLOBAL_CSS)
local_css(GRAFICO_CSS)


# =========================
# FUNZIONI UTILI
# =========================

def normalizza_dataframe_yfinance(data):
    """
    Alcune versioni di yfinance possono restituire colonne MultiIndex.
    Questa funzione rende il dataframe più semplice da usare.
    """
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data


def valore_float(valore):
    """
    Converte in modo sicuro un valore pandas/numpy in float.
    Evita errori quando yfinance restituisce Series invece di scalari.
    """
    if isinstance(valore, pd.Series):
        valore = valore.dropna()

        if valore.empty:
            return None

        valore = valore.iloc[0]

    if pd.isna(valore):
        return None

    return float(valore)


# =========================
# TICKER SELEZIONATO
# =========================

ticker = st.session_state.get("ticker_selezionato", "AAPL")

st.markdown(
    f"<h1>Analisi Quantitativa: {ticker}</h1>",
    unsafe_allow_html=True
)

if st.button("⬅️ Torna alla Dashboard"):
    st.switch_page("pages/dashboard.py")


# =========================
# DOWNLOAD DATI
# =========================

try:
    data = yf.download(
        ticker,
        period="2y",
        interval="1d",
        progress=False,
        auto_adjust=False
    )

    if data.empty:
        st.error(f"Dati non disponibili per {ticker}.")
        st.stop()

    data = normalizza_dataframe_yfinance(data)

    colonne_richieste = ["Open", "High", "Low", "Close"]

    for colonna in colonne_richieste:
        if colonna not in data.columns:
            st.error(f"Colonna mancante nei dati scaricati: {colonna}")
            st.stop()

    data = data.dropna(subset=colonne_richieste)

    if data.empty:
        st.error(f"Dati incompleti per {ticker}.")
        st.stop()


    # =========================
    # METRICHE
    # =========================

    prezzo = valore_float(data["Close"].iloc[-1])
    max_52w = valore_float(data["High"].tail(252).max())
    min_52w = valore_float(data["Low"].tail(252).min())

    if prezzo is None or max_52w is None or min_52w is None:
        st.error(f"Impossibile calcolare le metriche per {ticker}.")
        st.stop()

    m1, m2, m3 = st.columns(3)

    m1.metric("Prezzo", f"$ {prezzo:.2f}")
    m2.metric("Max 52W", f"$ {max_52w:.2f}")
    m3.metric("Min 52W", f"$ {min_52w:.2f}")


    # =========================
    # GRAFICO CANDELE
    # =========================

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=data.index,
                open=data["Open"],
                high=data["High"],
                low=data["Low"],
                close=data["Close"],
                name=ticker
            )
        ]
    )

    fig.update_layout(
        template="plotly_dark",
        height=650,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        title=f"Andamento {ticker} - Ultimi 2 anni",
        xaxis_title="Data",
        yaxis_title="Prezzo"
    )

    st.plotly_chart(fig, use_container_width=True)


except Exception as e:
    st.error(f"Errore durante il caricamento del grafico per {ticker}: {e}")
