import streamlit as st
import yfinance as yf
import os
import pandas as pd
from streamlit_sortables import sort_items

# --- PROTEZIONE TOTALE ---
if not st.session_state.get("authenticated", False):
    st.error("Accesso non autorizzato.")
    if st.button("Torna al Login"):
        st.switch_page("main.py")
    st.stop()

# --- CARICAMENTO CSS ---
def local_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("css/global.css")
local_css("css/dashboard.css")

# --- LOGICA DATI ---
FILE_WATCHLIST = "watchlist.txt"

def carica_ticker_da_file():
    if os.path.exists(FILE_WATCHLIST):
        with open(FILE_WATCHLIST, "r", encoding="utf-8") as f:
            return [line.strip().upper() for line in f.readlines() if line.strip()]
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]

def salva_ticker_su_file(lista_ticker):
    with open(FILE_WATCHLIST, "w", encoding="utf-8") as f:
        for tkr in lista_ticker: f.write(f"{tkr}\n")

if "lista_tickers" not in st.session_state:
    st.session_state["lista_tickers"] = carica_ticker_da_file()

st.markdown('<div class="main-title">Monitoraggio Globale Watchlist</div>', unsafe_allow_html=True)

# Gestione Watchlist
with st.expander("🛠️ Configura Watchlist", expanded=False):
    nuovo_ticker = st.text_input("Aggiungi Ticker:", key="txt_add").upper().strip()
    if st.button("Aggiungi alla lista"):
        if nuovo_ticker and nuovo_ticker not in st.session_state["lista_tickers"]:
            st.session_state["lista_tickers"].append(nuovo_ticker)
            salva_ticker_su_file(st.session_state["lista_tickers"])
            st.rerun()

    lista_prima = list(st.session_state["lista_tickers"])
    lista_dopo = sort_items(lista_prima, direction="vertical", key="drag_drop")
    if lista_dopo != lista_prima:
        st.session_state["lista_tickers"] = lista_dopo
        salva_ticker_su_file(lista_dopo)
        st.rerun()

# Rendering Tabella
st.markdown("---")
for tkr in list(st.session_state["lista_tickers"]):
    try:
        stock = yf.Ticker(tkr)
        hist = stock.history(period="2y", interval="1wk")
        if hist.empty: continue
        
        # Converte in float per evitare errori
        px = float(hist['Close'].iloc[-1])
        sma_val = hist['Close'].rolling(200).mean().iloc[-1]
        
        # Gestione valori mancanti (NaN)
        if pd.isna(sma_val):
            sma_str = "N/D"
            dist_str = "N/D"
        else:
            dist = ((px - sma_val) / sma_val) * 100
            sma_str = f"$ {sma_val:.2f}"
            dist_str = f"{dist:.2f} %"
        
        cols = st.columns([1, 2, 2, 2, 2, 1])
        with cols[0]:
            if st.button("📈", key=f"graf_{tkr}"):
                st.session_state['ticker_selezionato'] = tkr
                st.switch_page("pages/grafico.py") # CORRETTO: usa pages/
        with cols[1]: st.markdown(f"**{tkr}**")
        with cols[2]: st.markdown(f"$ {px:.2f}")
        with cols[3]: st.markdown(sma_str)
        with cols[4]: st.markdown(dist_str)
        with cols[5]:
            if st.button("🗑️", key=f"del_{tkr}"):
                st.session_state["lista_tickers"].remove(tkr)
                salva_ticker_su_file(st.session_state["lista_tickers"])
                st.rerun()
        st.divider()
    except Exception:
        continue
