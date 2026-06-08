import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- GESTIONE COSTRUZIONE E PERSISTENZA DELLA LISTA (DATABASE CLOUD) ---
# Proviamo a leggere la lista permanente salvata nel database di Streamlit
if "lista_tickers" not in st.session_state:
    try:
        # Carica la lista salvata sul cloud (se esiste)
        lista_salvata = st.experimental_kv.get("watchlist_permanente")
        if lista_salvata is not None and isinstance(lista_salvata, list):
            st.session_state["lista_tickers"] = lista_salvata
        else:
            # Se il database è vuoto, carichiamo i titoli di default dai Secrets o standard
            if "watchlist" in st.secrets and "tickers" in st.secrets["watchlist"]:
                st.session_state["lista_tickers"] = list(st.secrets["watchlist"]["tickers"])
            else:
                st.session_state["lista_tickers"] = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]
            # Salviamo la lista iniziale nel database cloud
            st.experimental_kv.set("watchlist_permanente", st.session_state["lista_tickers"])
    except:
        # Fallback di sicurezza in caso lo storage non sia ancora pronto
        st.session_state["lista_tickers"] = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]

st.title("📊 Monitoraggio Watchlist Magnifici 7")
st.markdown("I dati e le distanze dalla **SMA 200 Settimanale** si aggiornano automaticamente.")

# --- SEZIONE GESTIONE TICKER (AGGIUNGI) ---
with st.expander("🛠️ Gestisci i titoli della Watchlist (Modifiche Permanenti)", expanded=False):
    col_add_input, col_add_btn = st.columns([7, 3])
    with col_add_input:
        nuovo_ticker = st.text_input("Inserisci un nuovo Ticker (es. NFLX, BRK-B):").upper().strip()
    with col_add_btn:
        st.write("") # Spaziatori
        st.write("") 
        if st.button("➕ Aggiungi", use_container_width=True):
            if nuovo_ticker:
                if nuovo_ticker not in st.session_state["lista_tickers"]:
                    try:
                        # Verifica se esiste su Yahoo Finance
                        t = yf.Ticker(nuovo_ticker)
                        hist = t.history(period="1wk")
                        if not hist.empty:
                            # 1. Aggiungi alla sessione corrente
                            st.session_state["lista_tickers"].append(nuovo_ticker)
                            # 2. Salva permanentemente nel database Cloud
                            st.experimental_kv.set("watchlist_permanente", st.session_state["lista_tickers"])
                            st.success(f"Aggiunto permanentemente: {nuovo_ticker}")
                            st.rerun()
                        else:
                            st.error("Ticker non trovato su Yahoo Finance.")
                    except:
                        st.error("Errore durante la verifica del ticker.")
                else:
                    st.warning("Questo ticker è già presente nella lista.")
            else:
                st.warning("Inserisci un testo valido.")

st.markdown("---")

if not st.session_state["lista_tickers"]:
    st.info("La tua watchlist è vuota. Aggiungi un ticker usando il box sopra per iniziare.")
else:
    # --- COSTRUZIONE TABELLA ---
    header_cols = st.columns([1, 2, 2, 2, 2, 1])
    with header_cols[0]: st.markdown("**GRAFICO**")
    with header_cols[1]: st.markdown("**TICKER**")
    with header_cols[2]: st.markdown("**PREZZO CORRENTE**")
    with header_cols[3]: st.markdown("**SMA 200W**")
    with header_cols[4]: st.markdown("**DISTANZA % / AZIONE**")
    with header_cols[5]: st.markdown("**ELIMINA**")
    st.markdown("---")

    def calcola_sma200_settimanale(ticker_name):
        try:
            stock = yf.Ticker(ticker_name)
            df = stock.history(period="max", interval="1wk")
            if len(df) < 200:
                return None, None, None
            df['SMA200_W'] = df['Close'].rolling(window=200).mean()
            px_ult = df['Close'].iloc[-1]
            sma_ult = df['SMA200_W'].iloc[-1]
            dist_pct = ((px_ult - sma_ult) / sma_ult) * 100
            return px_ult, sma_ult, dist_pct
        except:
            return None, None, None

    for tkr in list(st.session_state["lista_tickers"]):
        px, sma, dist = calcola_sma200_settimanale(tkr)
        
        if px is not None:
            row_cols = st.columns([1, 2, 2, 2, 2, 1])
            
            with row_cols[0]:
                if st.button("📈", key=f"btn_graf_{tkr}"):
                    st.session_state['ticker_selezionato'] = tkr
                    st.switch_page("pagine/grafico.py")
            
            with row_cols[1]:
                st.markdown(f"**{tkr}**")
                
            with row_cols[2]:
                st.markdown(f"$ {px:.2f}")
                
            with row_cols[3]:
                st.markdown(f"$ {sma:.2f}")
                
            with row_cols[4]:
                colore = "#26a69a" if dist >= 0 else "#ef5350"
                segno = "+" if dist > 0 else ""
                st.markdown(f"<span style='color:{colore}; font-weight:bold;'>{segno}{dist:.2f} %</span>", unsafe_allow_html=True)
                
            with row_cols[5]:
                if st.button("🗑️", key=f"btn_del_{tkr}"):
                    # 1. Rimuovi dalla sessione corrente
                    st.session_state["lista_tickers"].remove(tkr)
                    # 2. Aggiorna permanentemente il database Cloud
                    st.experimental_kv.set("watchlist_permanente", st.session_state["lista_tickers"])
                    st.toast(f"Rimosso permanentemente {tkr}.")
                    st.rerun()
            
            st.markdown("<hr style='margin:0.5em 0; border-top: 1px solid rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
