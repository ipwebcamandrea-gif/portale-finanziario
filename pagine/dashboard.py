import streamlit as st
import yfinance as yf
import os
from streamlit_sortables import sort_items

# --- CONTROLLO ACCESSO ---
if not st.session_state.get('authenticated', False):
    st.error("Accesso non autorizzato. Torna alla home.")
    if st.button("Torna al Login"): st.switch_page("main.py")
    st.stop()

def local_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("css/global.css")
local_css("css/dashboard.css")

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
st.markdown('<div class="subtitle">Analisi quantitativa e distanze metriche dalla SMA 200 Settimanale</div>', unsafe_allow_html=True)

with st.expander("🛠️ Configurazione Watchlist & Drag-and-Drop", expanded=False):
    st.markdown("### ➕ Inserisci un nuovo asset")
    col1, col2 = st.columns([7, 3])
    with col1: nuovo_ticker = st.text_input("Ticker (es. NFLX):", key="txt_nuovo_tkr").upper().strip()
    with col2: aggiungi = st.button("Aggiungi", use_container_width=True)

    if aggiungi and nuovo_ticker:
        if nuovo_ticker not in st.session_state["lista_tickers"]:
            st.session_state["lista_tickers"].append(nuovo_ticker)
            salva_ticker_su_file(st.session_state["lista_tickers"])
            st.rerun()

    st.markdown("---")
    st.markdown("### ↕️ Organizza Sequenza")
    lista_prima = list(st.session_state["lista_tickers"])
    lista_dopo = sort_items(lista_prima, direction="vertical", key="drag_drop_watchlist")
    if lista_dopo != lista_prima:
        st.session_state["lista_tickers"] = lista_dopo
        salva_ticker_su_file(lista_dopo)
        st.rerun()

# --- TABELLA FINANZIARIA ---
for tkr in list(st.session_state["lista_tickers"]):
    try:
        px, sma, dist = calcola_sma200_settimanale(tkr) # Implementa la tua funzione di calcolo qui
        if px is None: continue
        row = st.columns([1, 2, 2, 2, 2, 1])
        with row[0]: 
            if st.button("📈", key=f"graf_{tkr}"):
                st.session_state['ticker_selezionato'] = tkr
                st.switch_page("pagine/grafico.py")
        with row[1]: st.markdown(f"**{tkr}**")
        with row[2]: st.markdown(f"$ {px:.2f}")
        with row[3]: st.markdown(f"$ {sma:.2f}")
        with row[4]: st.markdown(f"{dist:.2f} %")
        with row[5]: 
            if st.button("🗑️", key=f"del_{tkr}"):
                st.session_state["lista_tickers"].remove(tkr)
                salva_ticker_su_file(st.session_state["lista_tickers"])
                st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
    except: continue
