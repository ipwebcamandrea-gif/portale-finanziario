import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- CARICAMENTO FILE CSS DALLA CARTELLA DEDICATA ---
# Punta direttamente alla nuova cartella 'css' nella root del progetto
css_path = os.path.join("css", "grafico.css")

if os.path.exists(css_path):
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- LOGICA DELLA PAGINA GRAFICO ---
# Recupero dinamico dal click sulla dashboard, di default carica Microsoft (MSFT)
ticker = st.session_state.get('ticker_selezionato', 'MSFT')

st.title(f"📈 Analisi Tecnica Avanzata: {ticker}")
if st.button("← Torna alla Dashboard Watchlist"):
    st.switch_page("pagine/dashboard.py")

def calcola_wma(serie, window):
    pesi = np.arange(1, window + 1)
    return serie.rolling(window).apply(lambda x: np.dot(x, pesi) / pesi.sum(), raw=True)

# Recupero Storico Completo
stock = yf.Ticker(ticker)
df_chart = stock.history(period="max", interval="1wk")

if len(df_chart) >= 200:
    df_chart.index = df_chart.index.tz_localize(None)
    
    # Parametri Calcolo Standard
    df_chart['WMA21'] = calcola_wma(df_chart['Close'], 21)
    df_chart['WMA50'] = calcola_wma(df_chart['Close'], 50)
    df_chart['WMA200'] = calcola_wma(df_chart['Close'], 200)
    df_chart['EMA200'] = df_chart['Close'].ewm(span=200, adjust=False).mean()
    df_chart['SMA200'] = df_chart['Close'].rolling(window=200).mean()
    
    # MACD
    df_chart['EMA_Fast'] = df_chart['Close'].ewm(span=12, adjust=False).mean()
    df_chart['EMA_Slow'] = df_chart['Close'].ewm(span=26, adjust=False).mean()
    df_chart['MACD'] = df_chart['EMA_Fast'] - df_chart['EMA_Slow']
    df_chart['MACD_Signal'] = df_chart['MACD'].ewm(span=9, adjust=False).mean()
    df_chart['MACD_Hist'] = df_chart['MACD'] - df_chart['MACD_Signal']
    
    # Stochastic RSI
    delta = df_chart['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=20).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=20).mean()
    rs = gain / loss.replace(0, np.inf)
    df_chart['RSI'] = 100 - (100 / (1 + rs))
    rsi_min = df_chart['RSI'].rolling(window=20).min()
    rsi_max = df_chart['RSI'].rolling(window=20).max()
    df_chart['StochRSI'] = (df_chart['RSI'] - rsi_min) / (rsi_max - rsi_min) * 100
    df_chart['StochRSI_K'] = df_chart['StochRSI'].rolling(window=5).mean()
    df_chart['StochRSI_D'] = df_chart['StochRSI_K'].rolling(window=5).mean()
    
    # Filtro grafico dal 2019 ad oggi
    df_plot = df_chart.loc["2019-01-01":].copy()
    
    prezzo_ult = df_plot['Close'].iloc[-1]
    sma200_ult = df_plot['SMA200'].iloc[-1]
    df_52w = df_plot.tail(52)
    max_52w = float(df_52w['High'].max())
    min_52w = float(df_52w['Low'].min())
    
    dist_sma200 = ((prezzo_ult - sma200_ult) / sma200_ult) * 100
    dist_max52w = ((prezzo_ult - max_52w) / max_52w) * 100
    dist_min52w = ((prezzo_ult - min_52w) / min_52w) * 100

    st.subheader(f"Grafico Settimanale (Weekly) - {ticker}")

    # Costruzione Figure Multi-Panel Plotly
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.04, 
        row_heights=[0.60, 0.20, 0.20],
        specs=[[{"secondary_y": True}], [{}], [{}]]
    )
    
    # Candlestick principale
    fig.add_trace(go.Candlestick(
        x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
        low=df_plot['Low'], close=df_plot['Close'], name="Prezzo"
    ), row=1, col=1, secondary_y=False)
    
    # Tracciamento Medie Mobili
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['WMA21'], line=dict(color='white', width=1.2), name='WMA 21'), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['WMA50'], line=dict(color='green', width=1.2), name='WMA 50'), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['WMA200'], line=dict(color='#00bcff', width=1.2), name='WMA 200'), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA200'], line=dict(color='yellow', width=1.2), name='EMA 200'), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], line=dict(color='orange', width=2), name='SMA 200 W'), row=1, col=1, secondary_y=False)
    
    # Linee Orizzontali di Riferimento (Max/Min e QUOTAZIONE ATTUALE)
    fig.add_trace(go.Scatter(x=[df_plot.index[0], df_plot.index[-1]], y=[max_52w, max_52w], line=dict(color='#ff3399', width=1.5, dash='dash'), name='Max 52W'), row=1, col=1)
    fig.add_trace(go.Scatter(x=[df_plot.index[0], df_plot.index[-1]], y=[min_52w, min_52w], line=dict(color='#33ccff', width=1.5, dash='dash'), name='Min 52W'), row=1, col=1)
    
    # Quotazione corrente tratteggiata sottile ad alta visibilità
    fig.add_trace(go.Scatter(x=[df_plot.index[0], df_plot.index[-1]], y=[prezzo_ult, prezzo_ult], line=dict(color='#e0e0e0', width=1.5, dash='dot'), name='Quota Corrente'), row=1, col=1)
    
    # Etichette di quota laterali destre (Evitano la sovrapposizione sul titolo del grafico)
    fig.add_annotation(x=df_plot.index[-1], y=prezzo_ult, text=f"Corrente: {prezzo_ult:.2f}", showarrow=False, xanchor="left", xshift=8, font=dict(size=11, color="black"), bgcolor="#e0e0e0", row=1, col=1)
    fig.add_annotation(x=df_plot.index[-1], y=sma200_ult, text=f"SMA200: {sma200_ult:.2f} ({dist_sma200:+.2f}%)", showarrow=False, xanchor="left", xshift=8, font=dict(size=11, color="black"), bgcolor="orange", row=1, col=1)
    fig.add_annotation(x=df_plot.index[-1], y=max_52w, text=f"Max52W: {max_52w:.2f} ({dist_max52w:+.2f}%)", showarrow=False, xanchor="left", xshift=8, font=dict(size=11, color="white"), bgcolor="#ff3399", row=1, col=1)
    fig.add_annotation(x=df_plot.index[-1], y=min_52w, text=f"Min52W: {min_52w:.2f} ({dist_min52w:+.2f}%)", showarrow=False, xanchor="left", xshift=8, font=dict(size=11, color="black"),
