import streamlit as st


# =========================
# PROTEZIONE LOGIN
# =========================

if not st.session_state.get("authenticated", False):
    st.error("Accesso non autorizzato.")

    if st.button("Torna al Login"):
        st.switch_page("main.py")

    st.stop()


# =========================
# PAGINA PORTAFOGLIO
# =========================

st.title("💼 Il Mio Portafoglio")

st.info(
    "Questa sezione è pronta. "
    "Qui potremo sviluppare la logica per tracciare le tue posizioni reali."
)


# =========================
# NAVIGAZIONE
# =========================

if st.button("⬅️ Torna alla Dashboard"):
    st.switch_page("pages/dashboard.py")
