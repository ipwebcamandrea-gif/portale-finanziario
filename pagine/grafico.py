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

# CONTROLLO DI SICUREZZA: Se il selettore perde lo stato o restituisce None, forziamo il default su "W"
if not scelta_tf or scelta_tf not in ["D", "W", "M"]:
    scelta_tf = "W"

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
    # Caso "W" o ripiego di sicurezza
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
    sma200_ult = df_plot['SMA200'].iloc[-1]
    
    # Calcolo Max e Min a 52 settimane (1 anno mobile)
    df_52w = df_plot.tail(finestra_52w)
    max_52w = float(df_52w['High'].max())
    min_52w = float(df_52w['Low'].min())
    
    dist_sma200 = ((prezzo_ult - sma200_ult) / sma200_ult) * 100
    dist_max52w = ((prezzo_ult - max_52w) / max_52w) * 100
    dist_min52w = ((prezzo_ult - min_52w) / min_52w) * 100

    st.subheader(f"Grafico {titolo_grafico} - {ticker}")

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
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], line=dict(color='orange', width=2), name=label_media), row=1, col=1, secondary_y=False)
    
    # Linee Orizzontali di Riferimento
    fig.add_trace(go.Scatter(x=[df_plot.index[0], df_plot.index[-1]], y=[max_52w, max_52w], line=dict(color='#ff3399', width=1.5, dash='dash'), name='Max 1 Anno'), row=1, col=1)
    fig.add_trace(go.Scatter(x=[df_plot.index[0], df_plot.index[-1]], y=[min_52w, min_52w], line=dict(color='#33ccff', width=1.5, dash='dash'), name='Min 1 Anno'), row=1, col=1)
    fig.add_trace(go.Scatter(x=[df_plot.index[0], df_plot.index[-1]], y=[prezzo_ult, prezzo_ult], line=dict(color='#e0e0e0', width=1.5, dash='dot'), name='Quota Corrente'), row=1, col=1)
    
    # Etichette di quota laterali destre
    fig.add_annotation(x=df_plot.index[-1], y=prezzo_ult, text=f"Corrente: {prezzo_ult:.2f}", showarrow=False, xanchor="left", xshift=8, font=dict(size=11, color="black"), bgcolor="#e0e0e0", row=1, col=1)
    fig.add_annotation(x=df_plot.index[-1], y=sma200_ult, text=f"SMA200: {sma200_ult:.2f} ({dist_sma200:+.2f}%)", showarrow=False, xanchor="left", xshift=8, font=dict(size=11, color="black"), bgcolor="orange", row=1, col=1)
    fig.add_annotation(x=df_plot.index[-1], y=max_52w, text=f"Max 1A: {max_52w:.2f} ({dist_max52w:+.2f}%)", showarrow=False, xanchor="left", xshift=8, font=dict(size=11, color="white"), bgcolor="#ff3399", row=1, col=1)
    fig.add_annotation(x=df_plot.index[-1], y=min_52w, text=f"Min 1A: {min_52w:.2f} ({dist_min52w:+.2f}%)", showarrow=False, xanchor="left", xshift=8, font=dict(size=11, color="black"), bgcolor="#33ccff", row=1, col=1)
    
    # Volumi
    colori_volumi = ['rgba(38, 166, 154, 0.15)' if c >= o else 'rgba(239, 83, 80, 0.15)' for c, o in zip(df_plot['Close'], df_plot['Open'])]
    fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], marker_color=colori_volumi, name="Volume", showlegend=False), row=1, col=1, secondary_y=True)
    
    # Sotto-Riquadro 2: Stoch RSI
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['StochRSI_K'], line=dict(color='#17a2b8', width=1.5), name="Stoch RSI %K"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['StochRSI_D'], line=dict(color='#ffc107', width=1.2), name="Stoch RSI %D"), row=2, col=1)
    
    # Sotto-Riquadro 3: MACD
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MACD'], line=dict(color='#007bff', width=1.5), name="MACD"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MACD_Signal'], line=dict(color='#dc3545', width=1.5), name="Signal"), row=3, col=1)
    colori_macd_hist = ['#26a69a' if v >= 0 else '#ef5350' for v in df_plot['MACD_Hist']]
    fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['MACD_Hist'], marker_color=colori_macd_hist, name='Hist'), row=3, col=1)
    
    # Layout finale pulito Stile Dark
    fig.update_layout(
        template="plotly_dark", height=850, xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=160, t=25, b=10), paper_bgcolor='#131722', plot_bgcolor='#131722',
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        hovermode="x unified"
    )
    fig.update_yaxes(range=[0, df_plot['Volume'].max() * 4], showgrid=False, showticklabels=False, row=1, col=1, secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning(f"Storico insufficiente su questo titolo per estrarre la media a 200 periodi in modalità {scelta_tf}.")
