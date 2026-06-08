import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configurazione della lista dei Magnifici 7
TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA']

def calcola_distanze():
    dati_finali = []
    
    for t in TICKERS:
        try:
            stock = yf.Ticker(t)
            # Scarichiamo lo storico settimanale (ci serve per la SMA 200W)
            df = stock.history(period="max", interval="1wk")
            
            if len(df) >= 200:
                # Calcolo della Media Mobile Semplice a 200 settimane
                df['SMA200_W'] = df['Close'].rolling(window=200).mean()
                
                prezzo_corrente = df['Close'].iloc[-1]
                sma200_w = df['SMA200_W'].iloc[-1]
                
                # Calcolo della distanza percentuale
                distanza = ((prezzo_corrente - sma200_w) / sma200_w) * 100
                
                dati_finali.append({
                    'Ticker': t,
                    'Prezzo Corrente': f"$ {prezzo_corrente:.2f}",
                    'SMA 200W': f"$ {sma200_w:.2f}",
                    'Distanza %': distanza, # Mantenuto numerico per la formattazione colore
                    'raw_ticker': t
                })
        except Exception as e:
            pass
            
    return dati_finali

# --- INTERFACCIA DELLA DASHBOARD ---
st.title("📊 Monitoraggio Watchlist Magnifici 7")
st.write("I dati e le distanze dalla **SMA 200 Settimanale** si aggiornano automaticamente in background.")
st.markdown("---")

# Recupero dei dati aggiornati
lista_titoli = calcola_distanze()

if lista_titoli:
    # Intestazione della tabella con l'icona a sinistra
    col_icona, col_tk, col_pr, col_sma, col_dist = st.columns([0.8, 1.2, 2.0, 2.0, 2.5])
    
    with col_icona:
        st.markdown("**GRAFICO**")
    with col_tk:
        st.markdown("**TICKER**")
    with col_pr:
        st.markdown("**PREZZO CORRENTE**")
    with col_sma:
        st.markdown("**SMA 200W**")
    with col_dist:
        st.markdown("**DISTANZA % / AZIONE**")
        
    st.markdown("---")

    # Ciclo per popolare le righe della tabella
    for riga in lista_titoli:
        c_icona, c_tk, c_pr, c_sma, c_dist = st.columns([0.8, 1.2, 2.0, 2.0, 2.5])
        
        # 1. Pulsante icona a sinistra per aprire il grafico dedicato
        with c_icona:
            if st.button("📊", key=f"btn_{riga['raw_ticker']}"):
                st.session_state['ticker_selezionato'] = riga['raw_ticker']
                st.switch_page("pagine/grafico.py")
                
        # 2. Informazioni sul Ticker
        with c_tk:
            st.markdown(f"**{riga['Ticker']}**")
            
        # 3. Prezzo Corrente
        with c_pr:
            st.markdown(riga['Prezzo Corrente'])
            
        # 4. Valore della SMA200W
        with c_sma:
            st.markdown(riga['SMA 200W'])
            
        # 5. Distanza percentuale con colore dinamico (Verde se sopra la media, Rosso se sotto)
        with c_dist:
            valore_dist = riga['Distanza %']
            if valore_dist >= 0:
                colore = "#26a69a" # Verde trading
                segno = "+"
            else:
                colore = "#ef5350" # Rosso trading
                segno = ""
                
            st.markdown(f"<span style='color:{colore}; font-weight:bold;'>{segno}{valore_dist:.2f} %</span>", unsafe_allow_html=True)
            
        # Spazio di separazione millimetrico tra le righe
        st.markdown("<div style='margin-bottom: -10px;'></div>", unsafe_allow_html=True)
        st.markdown("---")
else:
    st.error("Impossibile recuperare i dati finanziari da Yahoo Finance al momento.")
