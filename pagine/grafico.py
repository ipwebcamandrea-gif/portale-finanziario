import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import os

if not st.session_state.get('authenticated', False):
    st.error("Devi prima effettuare l'accesso!")
    st.stop()
    
# --- FUNZIONE DI CARICAMENTO CSS DEDICATO ---
def local_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Carichiamo gli stili (assicurati che esistano nella cartella css/)
local_css("css/global.css")
# Se vuoi uno stile extra per questa pagina, crea css/grafico.css
if os.path.exists("css/grafico.css"):
    local_css("css/grafico.css")

# --- RECUPERO TICKER DALLA SESSIONE ---
ticker = st.session_state.get('ticker_selezionato', 'AAPL')

st.markdown(f'<div class="main-title">Analisi Grafica: {ticker}</div>', unsafe_allow_html=True)

# Pulsante per tornare indietro
if st.button("⬅️ Torna alla Dashboard"):
    st.switch_page("pagine/dashboard.py")

st.markdown("<br>", unsafe_allow_html=True)

# --- RECUPERO DATI E PLOTTING ---
try:
    df = yf.download(ticker, period="2y", interval="1d")
    
    if not df.empty:
        # Creazione grafico moderno con Plotly
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Market Data'
        )])
        
        # Stile del grafico (Dark Mode coerente)
        fig.update_layout(
            paper_bgcolor="#0e1117",
            plot_bgcolor="#0e1117",
            font_color="#8a99ad",
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=30, b=20),
            height=600
        )
        fig.update_xaxes(gridcolor="#222632")
        fig.update_yaxes(gridcolor="#222632")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Dati sintetici
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Prezzo Attuale", f"${df['Close'].iloc[-1]:.2f}")
        with col2: st.metric("Max 52 Sett.", f"${df['High'].rolling(252).max().iloc[-1]:.2f}")
        with col3: st.metric("Min 52 Sett.", f"${df['Low'].rolling(252).min().iloc[-1]:.2f}")
        
    else:
        st.error("Dati non disponibili per questo ticker.")
except Exception as e:
    st.error(f"Errore nel caricamento grafico: {e}")
