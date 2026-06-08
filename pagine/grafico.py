import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import os

# --- SICUREZZA ---
if not st.session_state.get('authenticated', False):
    st.error("Accesso negato.")
    if st.button("Torna al Login"): st.switch_page("main.py")
    st.stop()

# Caricamento Stili
def local_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("css/global.css")

ticker = st.session_state.get('ticker_selezionato', 'AAPL')
st.markdown(f'<div class="main-title">Analisi Quantitativa: {ticker}</div>', unsafe_allow_html=True)

if st.button("⬅️ Torna alla Dashboard"):
    st.switch_page("pagine/dashboard.py")

# Analisi Dati
try:
    data = yf.download(ticker, period="2y", interval="1d")
    if not data.empty:
        # Metriche
        m1, m2, m3 = st.columns(3)
        m1.metric("Prezzo", f"${data['Close'].iloc[-1]:.2f}")
        m2.metric("Max 52W", f"${data['High'].tail(252).max():.2f}")
        m3.metric("Min 52W", f"${data['Low'].tail(252).min():.2f}")
        
        # Grafico
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
        fig.update_layout(template="plotly_dark", height=600, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Dati non disponibili.")
except Exception as e:
    st.error(f"Errore: {e}")
