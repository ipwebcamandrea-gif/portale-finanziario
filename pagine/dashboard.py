import streamlit as st
import yfinance as yf
import os
from streamlit_sortables import sort_items

# --- CONTROLLO ACCESSO: DEVE ESSERE QUI, SUBITO DOPO GLI IMPORT ---
if not st.session_state.get('authenticated', False):
    st.error("Accesso non autorizzato. Torna alla home.")
    if st.button("Torna al Login"): st.switch_page("main.py")
    st.stop() # FERMA IL CARICAMENTO DELLA PAGINA SE NON SEI LOGGATO

# --- CARICAMENTO STILI ---
def local_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("css/global.css")
local_css("css/dashboard.css")

# --- LOGICA DATI (Tutto questo gira solo se sei autenticato) ---
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

# ... (resto della logica che avevamo definito)
