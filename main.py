import streamlit as st

def check_password():
    """Restituisce True se l'utente ha inserito la password corretta memorizzata nei Secrets."""
    if "password_correct" not in st.session_state:
        st.title("🔒 Accesso Protetto Portale")
        st.markdown("Inserisci la password amministrativa per consultare la watchlist finanziaria.")
        
        # Input password
        st.text_input("Password:", type="password", key="pwd_input")
        if st.button("Accedi"):
            # Verifica rispetto al caveau sicuro di Streamlit Cloud
            if st.session_state["pwd_input"] == st.secrets["PASSWORD"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Password errata. Riprova.")
        return False
    return st.session_state["password_correct"]

# Eseguiamo il controllo prima di caricare qualsiasi logica di navigazione
if check_password():
    st.set_page_config(layout="wide", page_title="Stazione di Controllo SMA200W")
    
    # Definizione delle pagine all'interno della sottocartella 'pagine'
    pg = st.navigation([
        st.Page("pagine/dashboard.py", title="Dashboard Watchlist", icon="📊"),
        st.Page("pagine/grafico.py", title="Analisi Grafica Avanzata", icon="📈")
    ])
    pg.run()