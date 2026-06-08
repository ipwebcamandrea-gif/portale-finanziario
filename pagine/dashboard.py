import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configurazione Ticker e Parametri Fissi
tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "BRK-B", "NVDA", "META"]
SOGLIA_FISSA = 0.10  # 10%

@st.cache_data(ttl=60)
def elabora_dati_titolo(ticker):
    """Scarica lo storico ed estrae l'ultimo record calcolando la SMA 200W."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period="max", interval="1wk")
    if hist.empty or len(hist) < 200:
        return None
    hist.index = hist.index.tz_localize(None)
    hist['SMA_200_W'] = hist['Close'].rolling(window=200).mean()
    return hist.iloc[-1]

st.title("📊 Monitoraggio Watchlist Magnifici 7")
st.markdown("I dati e le distanze dalla **SMA 200 Settimanale** si aggiornano automaticamente in background.")

# Tabella dati calcolati
lista_record = []
for t in tickers:
    try:
        ultimo_record = elabora_dati_titolo(t)
        if ultimo_record is not None:
            prezzo_corrente = ultimo_record['Close']
            sma_200_w = ultimo_record['SMA_200_W']
            distanza = (prezzo_corrente - sma_200_w) / sma_200_w
            trigger_vicinanza = abs(distanza) <= SOGLIA_FISSA
            
            lista_record.append({
                "Ticker": t,
                "Prezzo Attuale": prezzo_corrente,
                "SMA 200 W": sma_200_w,
                "Distanza %": distanza * 100,
                "Trigger": trigger_vicinanza
            })
    except Exception:
        continue

df_watchlist = pd.DataFrame(lista_record)

# Visualizzazione custom a righe larghe (Sfrutta l'intera larghezza dello schermo del PC/Mobile)
st.markdown("---")
# Intestazione Tabella spaziosa
head_col1, head_col2, head_col3, head_col4 = st.columns([1.5, 2.5, 2.5, 2.5])
head_col1.markdown("**TICKER**")
head_col2.markdown("**PREZZO CORRENTE**")
head_col3.markdown("**SMA 200W**")
head_col4.markdown("**DISTANZA % / AZIONE**")
st.markdown("---")

for i, riga in df_watchlist.iterrows():
    # Evidenziazione condizionale se sotto soglia 10%
    container_stile = st.container()
    with container_stile:
        col1, col2, col3, col4 = st.columns([1.5, 2.5, 2.5, 2.5])
        
        # Colore ticker basato sul trigger
        if riga['Trigger']:
            col1.markdown(f"🚨 **{riga['Ticker']}** *(Sotto Soglia)*")
        else:
            col1.markdown(f"**{riga['Ticker']}**")
            
        col2.markdown(f"$ {riga['Prezzo Attuale']:.2f}")
        col3.markdown(f"$ {riga['SMA 200 W']:.2f}")
        
        # Allineamento bottone e percentuale nello stesso blocco visivo
        col_btn_txt, col_btn_act = col4.columns([1.2, 1.3])
        col_btn_txt.markdown(f"**{riga['Distanza %']:+.2f} %**")
        
        # Bottone interattivo per cambiare pagina e iniettare il ticker nello stato di sessione
        if col_btn_act.button("Vedi Grafico", key=f"btn_{riga['Ticker']}", use_container_width=True):
            st.session_state['ticker_selezionato'] = riga['Ticker']
            st.switch_page("pagine/grafico.py")
    st.markdown("<div style='margin-bottom: -10px;'></div>", unsafe_value=True)