import streamlit as st
import os

def local_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("css/global.css")

st.markdown('<div class="welcome-container">', unsafe_allow_html=True)
st.markdown('<div class="hero-title">FinancePortal 2026</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.subheader("Accedi al sistema")
    
    user = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Entra nella Dashboard"):
        # Qui mettiamo le credenziali (usa 'admin' o i tuoi segreti)
        if user == "admin" and password == "admin": 
            st.session_state['authenticated'] = True
            st.switch_page("pagine/dashboard.py")
        else:
            st.error("Credenziali non valide")
    st.markdown('</div>', unsafe_allow_html=True)
