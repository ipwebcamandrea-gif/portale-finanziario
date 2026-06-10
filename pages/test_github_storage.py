import streamlit as st

from utils.github_storage import github_storage_enabled, test_github_storage_connection


# =========================
# PROTEZIONE LOGIN
# =========================

if not st.session_state.get("authenticated", False):
    st.error("Accesso non autorizzato.")

    if st.button("Torna al Login"):
        st.switch_page("main.py")

    st.stop()


# =========================
# PAGINA TEST GITHUB STORAGE
# =========================

st.title("Test GitHub Storage")
st.caption("Pagina temporanea per verificare lettura di watchlists.json dal branch data-watchlists.")

if st.button("← Cockpit", key="test_github_back"):
    st.switch_page("pages/dashboard.py")

st.divider()

if not github_storage_enabled():
    st.error("GitHub storage non risulta abilitato nei Secrets Streamlit.")
    st.stop()

if st.button("Esegui test lettura GitHub", key="test_github_read"):
    try:
        result = test_github_storage_connection()
        st.success("Connessione GitHub OK. Lettura watchlists.json riuscita.")
        st.json(result)
    except Exception as error:
        st.error("Errore durante il test GitHub storage.")
        st.exception(error)
