import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os

# --- GESTIONE PERSISTENZA SU FILE LOCALE ---
FILE_WATCHLIST = "watchlist.txt"

def carica_ticker_da_file():
    """Legge i ticker dal file locale. Se il file non esiste, usa quelli di default."""
    if os.path.exists(FILE_WATCHLIST):
        with open(FILE_WATCHLIST, "r", encoding="utf-8") as f:
            ticker_salvati = [line.strip().upper() for line in f.readlines() if line.strip()]
            if ticker_salvati:
                return ticker_salvati
                
    # Default di backup se il file è vuoto o non esiste
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

st.title("📊 Monitoraggio Watchlist Magnifici 7")
st.markdown("I dati e le distanze dalla **SMA 200 Settimanale** si aggiornano automaticamente.")

# --- SEZIONE GESTIONE E RIORDINO TICKER ---
with st.expander("🛠️ Gestisci e Riordina la Watchlist (Modifiche Permanenti)", expanded=False):
    
    # 1. Tab per aggiungere nuovi elementi
    st.subheader("➕ Aggiungi un nuovo titolo")
    col_add_input, col_add_btn = st.columns([7, 3])
    with col_add_input:
        nuovo_ticker = st.text_input("Inserisci un nuovo Ticker (es. NFLX, BRK-B):", key="txt_nuovo_tkr").upper().strip()
    with col_add_btn:
        st.write("") # Spaziatori visivi
        st.write("") 
        if st.button("Aggiungi alla lista", use_container_width=True):
            if nuovo_ticker:
                if nuovo_ticker not in st.session_state["lista_tickers"]:
                    try:
                        t = yf.Ticker(nuovo_ticker)
                        hist = t.history(period="1wk")
                        if not hist.empty:
                            st.session_state["lista_tickers"].append(nuovo_ticker)
                            salva_ticker_su_file(st.session_state["lista_tickers"])
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
    
    # 2. Strumento di Riordino Drag & Drop / Spostamento
    st.subheader("↕️ Cambia l'ordine dei titoli")
    st.caption("Trascina le righe tenendo premuto il quadratino a sinistra oppure usa le frecce per riordinare la tabella.")
    
    # Creiamo un piccolo DataFrame di supporto per l'editor di riordino
    df_ordinamento = pd.DataFrame({"Ticker": st.session_state["lista_tickers"]})
    
    # Mostriamo il data_editor che permette di spostare e riordinare le righe
    df_ordinato = st.data_editor(
        df_ordinamento,
        num_rows="fixed", # Blocchiamo il numero di righe per usare l'ordinamento nativo
        use_container_width=True,
        disabled=["Ticker"], # Impediamo la modifica del testo, vogliamo solo spostare le righe
        key="editor_riordino"
    )
    
    # Pulsante per salvare la nuova sequenza scelta dall'utente
    if st.button("💾 Salva Nuovo Ordine", use_container_width=True, type="primary"):
        nuova_lista = df_ordinato["Ticker"].tolist()
        st.session_state["lista_tickers"] = nuova_lista
        salva_ticker_su_file(nuova_lista)
        st.success("Nuovo ordine salvato con successo!")
        st.rerun()

st.markdown("---")

if not st.session_state["lista_tickers"]:
    st.info("La tua watchlist è vuota. Aggiungi un ticker usando il box sopra per iniziare.")
else:
    # --- COSTRUZIONE TABELLA FINANZIARIA ---
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
                    st.session_state["lista_tickers"].remove(tkr)
                    salva_ticker_su_file(st.session_state["lista_tickers"])
                    st.toast(f"Rimosso permanentemente {tkr}.")
                    st.rerun()
            
            st.markdown("<hr style='margin:0.5em 0; border-top: 1px solid rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
