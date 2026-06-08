import streamlit as st
import os

# 1. Configurazione iniziale della pagina
st.set_page_config(page_title="FinancePortal 2026", layout="centered")

# 2. Inizializzazione dello stato di autenticazione
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# 3. Caricamento del file CSS (se presente)
if os.path.exists("css/global.css"):
    with open("css/global.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 4. Interfaccia di Login
st.markdown('<div class="welcome-container">', unsafe_allow_html=True)
st.markdown('<div class="hero-title">FinancePortal 2026</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.subheader("Accedi al sistema")
    
    # Usiamo st.form per evitare che la pagina si ricarichi e perda i dati inseriti
    with st.form("login_form"):
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        # Bottone di invio del form
        submitted = st.form_submit_button("Entra nella Dashboard")
        
        if submitted:
            # Controllo credenziali corrette
            # Nota: .strip() rimuove eventuali spazi vuoti accidentali
            if user.strip() == "admin" and password.strip() == "Pippolo001+1": 
                st.session_state["authenticated"] = True
                st.success("Accesso effettuato!")
                st.switch_page("pagine/dashboard.py")
            else:
                st.session_state["authenticated"] = False
                st.error("Credenziali non valide")
    
    st.markdown('</div>', unsafe_allow_html=True)
