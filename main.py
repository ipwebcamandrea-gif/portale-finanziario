import streamlit as st

# Configurazione della pagina (deve essere la primissima istruzione Streamlit)
st.set_page_config(
    page_title="Portale Finanziario",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNZIONE DI AUTENTICAZIONE ---
def check_password():
    """Restituisce True se l'utente ha inserito le credenziali corrette."""
    
    def login_form():
        """Mostra il form di login con Username e Password."""
        st.subheader("🔒 Accesso Riservato")
        username_input = st.text_input("Username", key="login_username")
        password_input = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Accedi", use_container_width=True):
            # Recuperiamo le credenziali salvate nei Secrets di Streamlit
            if "credentials" in st.secrets and "usernames" in st.secrets["credentials"]:
                secrets_users = st.secrets["credentials"]["usernames"]
                
                # Controllo se l'username esiste e se la password corrisponde
                if username_input in secrets_users and secrets_users[username_input] == password_input:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("😕 Username o Password errati.")
            else:
                st.error("🛠️ Errore di configurazione: credenziali non trovate nei Secrets.")

    # Se l'utente è già loggato, restituisce True direttamente
    if st.session_state.get("password_correct", False):
        return True

    # Altrimenti mostra il form e blocca il resto dell'app
    login_form()
    return False

# --- CONTROLLO ACCESSO ---
if check_password():
    # Pagina visibile nel menu
    page_dashboard = st.Page("pagine/dashboard.py", title="Dashboard Watchlist", icon="📊")
    
    # MODO CORRETTO DI NASCONDERE LA PAGINA: Usiamo position="hidden"
    # La pagina grafico rimane accessibile tramite st.switch_page ma sparisce completamente dal menu laterale!
    page_grafico = st.Page("pagine/grafico.py", title="Analisi Grafica Avanzata", icon="📈")
    
    # Passiamo entrambe le pagine alla navigazione in modo che Streamlit le riconosca entrambe ufficialmente
    pg = st.navigation([page_dashboard, page_grafico], position="hidden")
    
    # Avvia la navigazione dell'app
    pg.run()
