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
    
    # Se l'utente è già loggato, restituisce True direttamente
    if st.session_state.get("password_correct", False):
        return True

    # Mostra il form di login gestito con st.form per intercettare l'autofill del browser
    st.subheader("🔒 Accesso Riservato")
    
    with st.form("login_form", clear_on_submit=False):
        username_input = st.text_input("Username", autocomplete="username")
        password_input = st.text_input("Password", type="password", autocomplete="current-password")
        submit_button = st.form_submit_button("Accedi", use_container_width=True)
        
        if submit_button:
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

    return False

# --- CONTROLLO ACCESSO ---
if check_password():
    # Pagina visibile nel menu
    page_dashboard = st.Page("pagine/dashboard.py", title="Dashboard Watchlist", icon="📊")
    
    # La pagina grafico rimane accessibile tramite st.switch_page ma sparisce completamente dal menu laterale
    page_grafico = st.Page("pagine/grafico.py", title="Analisi Grafica Avanzata", icon="📈")
    
    # Passiamo entrambe le pagine alla navigazione con l'opzione nascosta
    pg = st.navigation([page_dashboard, page_grafico], position="hidden")
    
    # Avvia la navigazione dell'app
    pg.run()
