import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "BRK-B", "NVDA", "META"]
SOGLIA_FISSA = 0.10  # 10%

@st.cache_data(ttl=60)
def get_data(ticker):
    hist = yf.Ticker(ticker).history(period="1y", interval="1wk")
    hist['SMA_200'] = hist['Close'].rolling(200).mean()
    return hist.iloc[-1]

st.title("Watchlist Titoli (Soglia 10%)")

# Creazione tabella
data = []
for t in tickers:
    try:
        last = get_data(t)
        dist = (last['Close'] - last['SMA_200']) / last['SMA_200']
        data.append({"Ticker": t, "Prezzo": last['Close'], "Distanza %": dist * 100})
    except: continue

df = pd.DataFrame(data)

# Visualizzazione con bottone "Apri Grafico"
for i, row in df.iterrows():
    col1, col2, col3, col4 = st.columns([1, 2, 2, 2])
    col1.write(f"**{row['Ticker']}**")
    col2.write(f"${row['Prezzo']:.2f}")
    col3.write(f"{row['Distanza %']:.2f} %")
    if col4.button("Apri Grafico", key=row['Ticker']):
        st.session_state['ticker_selezionato'] = row['Ticker']
        st.switch_page("pagine/grafico.py")
