import streamlit as st
import os

# Pulizia forzata dello stato per evitare conflitti
if "authenticated" in st.session_state:
    st.session_state["authenticated"] = False

# Caricamento CSS
if os.path.exists("css/global.css"):
    with open("css/global.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown('<div class="welcome-container">', unsafe_allow_html=True)
st.markdown('<div class="hero-title">FinancePortal 2026</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.subheader("Accedi al sistema")
    
    # Campi di input
    user = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    # Bottone
    if st.button("Entra nella Dashboard"):
        # Controllo rigido (assicurati di scrivere 'admin' esattamente così)
        if user == "admin" and password == "admin": 
            st.session_state["authenticated"] = True
            st.switch_page("pagine/dashboard.py")
        else:
            st.error("Credenziali non valide")
    
    st.markdown('</div>', unsafe_allow_html=True)
