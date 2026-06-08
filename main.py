import streamlit as st
import os

# Inizializzazione sessione
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Caricamento CSS
if os.path.exists("css/global.css"):
    with open("css/global.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown('<div class="welcome-container">', unsafe_allow_html=True)
st.markdown('<div class="hero-title">FinancePortal 2026</div>', unsafe_allow_html=True)

# --- USO DEL FORM PER FISSARE GLI INPUT ---
with st.container():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.subheader("Accedi al sistema")
    
    with st.form("login_form"):
        # I campi sono dentro il form
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        # Il bottone di submit invia tutto il form insieme
        submitted = st.form_submit_button("Entra nella Dashboard")
        
        if submitted:
            # DEBUG: Ora vedrai che user e password avranno il valore corretto
            st.write(f"DEBUG - Input: User='{user}', Pass='{password}'")
            
            if user.strip() == "admin" and password.strip() == "admin": 
                st.session_state["authenticated"] = True
                st.success("Accesso effettuato!")
                st.switch_page("pagine/dashboard.py")
            else:
                st.session_state["authenticated"] = False
                st.error("Credenziali non valide")
    
    st.markdown('</div>', unsafe_allow_html=True)
