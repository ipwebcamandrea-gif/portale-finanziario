import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- CARICAMENTO FILE CSS IN MODO SICURO ---
css_path = os.path.join("css", "grafico.css")

if os.path.exists(css_path):
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except Exception as e:
        pass

# --- LOGICA DELLA PAGINA GRAFICO ---
ticker = st.session_state.get('ticker_selezionato', 'MSFT')

st.title(f"📈 Analisi Tecnica Avanzata: {ticker}")

# Riga di navigazione e controllo in alto
col_back, col_space = st.columns([3, 7])
with col_back:
    if st.button("← Torna alla Dashboard Watchlist", use_container_width=True):
        st.switch_page("pagine/dashboard.py")

st.markdown("---")

# --- SELEZIONE DEL TIMEFRAME COMPATTA (D / W / M) ---
scelta_tf = st.segmented_control(
    "Timeframe:",
    options=["D", "W", "M"],
    default="W"
)

# Mappatura dei parametri in base alla scelta dell'utente
if scelta_tf == "D":
    interval_yf = "1d"
    period_yf = "max"
    label_media = "SMA 200 Giorni"
    finestra_52w = 252  # Giorni di borsa aperta in un anno
    titolo_grafico = "Giornaliero (Daily)"
elif scelta_tf == "M":
    interval_yf = "1mo"
    period_yf = "max"
    label_media = "SMA 200 Mesi"
    finestra_52w = 12   # Mesi in un anno
    titolo_grafico = "Mensile (Monthly)"
else:
    # Di default: W (Settimanale)
    interval_yf = "1wk"
    period_yf = "max"
    label_media = "SMA 200 W"
    finestra_52w = 52   # Settimane in un anno
    titolo_grafico = "Settimanale (Weekly)"

def calcola_wma(serie, window):
    pesi = np.arange(1, window + 1)
    return serie.rolling(window).apply(lambda x: np.dot(x, pesi) / pesi.sum(), raw=True)

# Recupero Storico Completo
stock = yf.Ticker(ticker)
df_chart = stock.history(period=period_yf, interval=interval_yf)

if len(df_chart) >= 200:
    df_chart.index = df_chart.index.tz_localize(None)
    
    # Parametri Calcolo dinamici
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
    sma200_ult = df_plot['SMA200'].iloc
