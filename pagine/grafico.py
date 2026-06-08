import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Recupera il ticker scelto
ticker = st.session_state.get('ticker_selezionato', 'AAPL')
st.subheader(f"Analisi Grafica: {ticker} (Timeframe 1W)")

# Logica di calcolo (stessa usata in precedenza)
def calcola_wma(serie, window):
    pesi = np.arange(1, window + 1)
    return serie.rolling(window).apply(lambda x: np.dot(x, pesi) / pesi.sum(), raw=True)

stock = yf.Ticker(ticker)
df = stock.history(period="max", interval="1wk")
df.index = df.index.tz_localize(None)

# Indicatori
df['SMA200'] = df['Close'].rolling(200).mean()
# ... [inserisci qui i calcoli MACD e StochRSI del codice precedente] ...

# Grafico (con le label e la linea prezzo corrente)
fig = go.Figure()
# ... [inserisci qui il codice plotly] ...

st.plotly_chart(fig, use_container_width=True)
if st.button("← Torna alla Watchlist"):
    st.switch_page("pagine/dashboard.py")
