import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import os

# --- 1. SICUREZZA (CONTROLLO ACCESSO IMMEDIATO) ---
if not st.session_state.get('authenticated', False):
    st.error("Accesso non autorizzato. Torna alla home.")
    if st.button("Torna al Login"):
        st.switch_page("main.py")
    st.stop()

# --- 2. FUNZIONE CARICAMENTO CSS ---
def local_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Carichiamo gli stili globali per mantenere il look Dark Pro
local_css("css/global.css")

# --- 3. LOGICA DI NAVIGAZIONE E RECUPERO TICKER ---
ticker = st.session_state.get('ticker_selezionato', 'AAPL')

# Header stilizzato
st.markdown(f'<div class="main-title">Analisi Quantitativa: {ticker}</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Visualizzazione avanzata dei prezzi e metriche di supporto</div>', unsafe_allow_html=True)

# Pulsante di ritorno compatto
if st.button("⬅️ Torna alla Dashboard Generale"):
    st.switch_page("pagine/dashboard.py")

st.markdown("<br>", unsafe_allow_html=True)

# --- 4. RECUPERO DATI AVANZATO ---
try:
    # Scarichiamo dati giornalieri degli ultimi 2 anni per avere profondità
    data = yf.download(ticker, period="2y", interval="1d")
    
    if data is None or data.empty:
        st.error(f"Impossibile recuperare i dati per {ticker}. Verifica la connessione o il simbolo.")
    else:
        # Calcolo Metriche Pro
        ultimo_prezzo = data['Close'].iloc[-1]
        max_52w = data['High'].tail(252).max()
        min_52w = data['Low'].tail(252).min()
        variazione = ((data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100

        # Riga delle metriche stilizzate
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Ultimo Prezzo", f"$ {ultimo_prezzo:.2f}", f"{variazione:.2f}%")
        with m2:
            st.metric("Massimo 52 Sett.", f"$ {max_52w:.2f}")
        with m3:
            st.metric("Minimo 52 Sett.", f"$ {min_52w:.2f}")
        with m4:
            st.metric("Volume Odierno", f"{data['Volume'].iloc[-1]:,.0f}")

        st.markdown("---")

        # --- 5. CONFIGURAZIONE GRAFICO PLOTLY "TRADING VIEW STYLE" ---
        fig = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            increasing_line_color='#26a69a', # Verde TradingView
            decreasing_line_color='#ef5350', # Rosso TradingView
            name=ticker
        )])

        # Restyling completo del Layout del grafico
        fig.update_layout(
            paper_bgcolor="#0e1117", # Sfondo coordinato con global.css
            plot_bgcolor="#0e1117",
            font_color="#8a99ad",
            xaxis_rangeslider_visible=False, # Pulizia visiva
            height=600,
            margin=dict(l=10, r=10, t=10, b=10),
            hovermode="x unified",
            xaxis=dict(
                showgrid=True,
                gridcolor="#1e222d", # Griglia sottile stile scuro
                linecolor="#2a2e39"
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#1e222d",
                linecolor="#2a2e39",
                side="right" # Prezzo a destra come nei software pro
            )
        )

        # Visualizzazione Grafico
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # --- 6. TABELLA DATI RECENTI ---
        with st.expander("📂 Visualizza Storico Dati Recenti"):
            st.dataframe(data.tail(20).sort_index(ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Si è verificato un errore durante l'analisi: {e}")
