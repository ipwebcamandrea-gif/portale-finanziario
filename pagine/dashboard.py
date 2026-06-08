import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from streamlit_sortables import sort_items

# --- FUNZIONE DI CARICAMENTO CSS DEDICATO (PERCORSO ROOT) ---
def local_css(file_path):
    """Legge un file CSS locale dalla root e lo inietta nell'app Streamlit"""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Carichiamo i file di stile direttamente dalla cartella css nella root
local_css("css/global.css")
local_css("css/dashboard.css")

# --- GESTIONE PERSISTENZA SU FILE LOCALE ---
FILE_WATCHLIST = "watchlist.txt"

def carica_ticker_da_file():
    """Legge i ticker dal file locale. Se il file non esiste, usa quelli di default."""
    if os.path.exists(FILE_WATCHLIST):
        with open(FILE_WATCHLIST, "r", encoding="utf-8") as f:
            ticker_salvati = [line.strip().upper() for line in f.readlines() if line.strip()]
            if ticker_salvati:
                return ticker_salvati
                
    if "watchlist" in st.secrets and "tickers" in st.secrets["watchlist"]:
        return list(st.secrets["watchlist"]["tickers"])
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]

def salva_ticker_su_file(lista_ticker):
    """Scrive la lista ordinata nel file locale."""
    with open(FILE_WATCHLIST, "w", encoding="utf-8") as f:
        for tkr in lista_ticker:
            f.write(f"{tkr}\n")

# Inizializziamo lo stato della sessione leggendo dal file
if "lista_tickers" not in st.session_state:
    st.session_state["lista_tickers"] = carica_ticker_da_file()

# Intestazione della pagina con classi CSS dedicate
st.markdown('<div class="main-title">Monitoraggio Globale Watchlist</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Analisi quantitativa e distanze metriche dalla SMA 200 Settimanale</div>', unsafe_allow_html=True)

# --- SEZIONE GESTIONE E RIORDINO TICKER ---
with st.expander("🛠️ Configurazione Watchlist & Drag-and-Drop", expanded=False):
    
    st.markdown("### ➕ Inserisci un nuovo asset")
    col_add_input, col_add_btn = st.columns([7, 3])
    
    with col_add_input:
        nuovo_ticker = st.text_input("Simbolo del ticker (Yahoo Finance):", key="txt_nuovo_tkr", label_visibility="collapsed").upper().strip()
        
    with col_add_btn:
        esegui_aggiunta = st.button("Aggiungi alla lista", use_container_width=True)

    if esegui_aggiunta and nuovo_ticker:
        if nuovo_ticker not in st.session_state["lista_tickers"]:
            try:
                t = yf.Ticker(nuovo_ticker)
                hist = t.history(period="1wk")
                if not hist.empty:
                    st.session_state["lista_tickers"].append(nuovo_ticker)
                    salva_ticker_su_file(st.session_state["lista_tickers"])
                    st.success(f"Portato dentro: {nuovo_ticker}")
                    st.rerun()
                else:
                    st.error("Ticker non trovato o non valido su Yahoo Finance.")
            except:
                st.error("Errore di comunicazione durante la verifica.")
        else:
            st.warning("Questo ticker è già presente nella lista.")
                
    st.markdown("---")
    
    st.markdown("### ↕️ Organizza Sequenza")
    st.caption("Sposta i blocchi trascinandoli verticalmente. La griglia sotto seguirà l'ordine in tempo reale.")
    
    lista_prima = list(st.session_state["lista_tickers"])
    
    # Il componente restituisce la lista aggiornata ad ogni movimento (stilizzato via dashboard.css)
    lista_dopo = sort_items(lista_prima, direction="vertical", key="drag_drop_watchlist")
    
    if lista_dopo != lista_prima:
        st.session_state["lista_tickers"] = lista_dopo
        salva_ticker_su_file(lista_dopo)
        st.rerun()

st.markdown(" ")

# --- COSTRUZIONE TABELLA FINANZIARIA PRO ---
if not st.session_state["lista_tickers"]:
    st.info("La tua watchlist è attualmente vuota. Espandi il pannello sopra per aggiungere titoli.")
else:
    # Intestazioni di colonna stilizzate
    header_cols = st.columns([1, 2, 2, 2, 2, 1])
    with header_cols[0]: st.markdown('<div class="table-header">Grafico</div>', unsafe_allow_html=True)
    with header_cols[1]: st.markdown('<div class="table-header">Ticker</div>', unsafe_allow_html=True)
    with header_cols[2]: st.markdown('<div class="table-header">Prezzo</div>', unsafe_allow_html=True)
    with header_cols[3]: st.markdown('<div class="table-header">SMA 200W</div>', unsafe_allow_html=True)
    with header_cols[4]: st.markdown('<div class="table-header">Distanza %</div>', unsafe_allow_html=True)
    with header_cols[5]: st.markdown('<div class="table-header">Azione</div>', unsafe_allow_html=True)
    
    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    def calcola_sma200_settimanale(ticker_name):
        try:
            stock = yf.Ticker(ticker_name)
            df = stock.history(period="7y", interval="1wk")
            if df is None or df.empty or len(df) < 200:
                return None, None, None
            df['SMA200_W'] = df['Close'].rolling(window=200).mean()
            if 'SMA200_W' not in df or pd.isna(df['SMA200_W'].iloc[-1]):
                return None, None, None
            px_ult = df['Close'].iloc[-1]
            sma_ult = df['SMA200_W'].iloc[-1]
            dist_pct = ((px_ult - sma_ult) / sma_ult) * 100
            return px_ult, sma_ult, dist_pct
        except:
            return None, None, None

    # Ciclo di rendering protetto da eccezioni strutturali
    for tkr in list(st.session_state["lista_tickers"]):
        try:
            px, sma, dist = calcola_sma200_settimanale(tkr)
            
            # Se Yahoo Finance fallisce, saltiamo la riga elegantemente senza rompere la pagina
            if px is None or pd.isna(px):
                continue
                
            row_cols = st.columns([1, 2, 2, 2, 2, 1])
            
            # 1) Bottone apertura Grafico Avanzato
            with row_cols[0]:
                if st.button("📈", key=f"btn_graf_{tkr}"):
                    st.session_state['ticker_selezionato'] = tkr
                    st.switch_page("pagine/grafico.py")
            
            # 2) Simbolo Ticker
            with row_cols[1]:
                st.markdown(f"<div style='padding-top:5px; font-weight:700; color:#ffffff;'>{tkr}</div>", unsafe_allow_html=True)
                
            # 3) Ultimo Prezzo Disponibile
            with row_cols[2]:
                st.markdown(f"<div style='padding-top:5px; color:#e0e3eb;'>$ {px:.2f}</div>", unsafe_allow_html=True)
                
            # 4) Valore di Sostegno SMA200
            with row_cols[3]:
                st.markdown(f"<div style='padding-top:5px; color:#b2b5be;'>$ {sma:.2f}</div>", unsafe_allow_html=True)
                
            # 5) Distanza Percentuale Colorata (Verde / Rosso TradingView)
            with row_cols[4]:
                colore = "#26a69a" if dist >= 0 else "#ef5350"
                segno = "+" if dist > 0 else ""
                st.markdown(f"<div style='padding-top:5px; color:{colore}; font-weight:700;'>{segno}{dist:.2f} %</div>", unsafe_allow_html=True)
                
            # 6) Bottone Cancella asset
            with row_cols[5]:
                if st.button("🗑️", key=f"btn_del_{tkr}"):
                    st.session_state["lista_tickers"].remove(tkr)
                    salva_ticker_su_file(st.session_state["lista_tickers"])
                    st.toast(f"Rimosso {tkr}.")
                    st.rerun()
            
            # Divisore grafico sottile e moderno inserito tra i blocchi
            st.markdown("<hr style='margin:0.6em 0; border-top: 1px solid #222632;'>", unsafe_allow_html=True)
        except:
            continue
