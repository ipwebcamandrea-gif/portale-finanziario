import streamlit as st

st.set_page_config(page_title="Watchlist", layout="wide")

# 1. Inizializzazione della lista nello stato di sessione
if "my_watchlist" not in st.session_state:
    st.session_state["my_watchlist"] = ["AAPL", "TSLA", "NVDA"]

st.title("📊 La mia Watchlist")

# 2. Form per aggiungere un nuovo ticker
with st.form("add_ticker_form"):
    new_ticker = st.text_input("Inserisci simbolo ticker (es. BTC, GOOGL)")
    submitted = st.form_submit_button("Aggiungi alla lista")
    
    if submitted and new_ticker:
        ticker_clean = new_ticker.upper().strip()
        if ticker_clean not in st.session_state["my_watchlist"]:
            st.session_state["my_watchlist"].append(ticker_clean)
            st.rerun()
        else:
            st.warning("Ticker già presente in lista!")

# 3. Visualizzazione della lista
st.subheader("I tuoi titoli")

for ticker in st.session_state["my_watchlist"]:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write(f"### {ticker}")
        
    with col2:
        # Quando clicchi qui, passiamo il ticker tramite l'URL
        if st.button(f"📊 Analizza", key=f"btn_{ticker}"):
            st.query_params["ticker"] = ticker
            st.switch_page("pages/grafico.py")
            
    st.divider()

# 4. Bottone per tornare indietro
if st.button("Torna alla Dashboard"):
    st.switch_page("pages/dashboard.py")
