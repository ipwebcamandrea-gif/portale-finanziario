import streamlit as st
import os

# --- FUNZIONE DI CARICAMENTO CSS ---
def local_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Carichiamo lo stile globale che abbiamo già creato
local_css("css/global.css")

# --- CSS SPECIFICO PER LA PAGINA DI ACCESSO ---
st.markdown("""
<style>
    .welcome-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding-top: 100px;
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(90deg, #26a69a, #00b0ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .hero-subtitle {
        color: #8a99ad;
        font-size: 1.2rem;
        margin-bottom: 3rem;
    }
    .login-box {
        background-color: #161a25;
        padding: 40px;
        border-radius: 12px;
        border: 1px solid #222632;
        width: 100%;
        max-width: 400px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- LAYOUT PAGINA ---
st.markdown('<div class="welcome-container">', unsafe_allow_html=True)
st.markdown('<div class="hero-title">FinancePortal 2026</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Monitoraggio professionale, riordino intelligente.</div>', unsafe_allow_html=True)

# Contenitore Login
with st.container():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.subheader("Accedi al sistema")
    
    # Esempio di autenticazione semplice
    user = st.text_input("Username", placeholder="Inserisci username")
    password = st.text_input("Password", type="password", placeholder="Inserisci password")
    
    if st.button("Entra nella Dashboard", use_container_width=True):
        if user == "admin" and password == "admin": # Cambia con i tuoi credenziali/secrets
            st.session_state['authenticated'] = True
            st.switch_page("pagine/dashboard.py")
        else:
            st.error("Credenziali non valide")
    
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
