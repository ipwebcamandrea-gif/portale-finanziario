import streamlit as st


# =========================
# CHECK AUTH
# =========================

def is_authenticated():
    return st.session_state.get("authenticated", False)


# =========================
# PROTEZIONE PAGINE
# =========================

def require_login():
    if not is_authenticated():
        st.error("Accesso non autorizzato.")

        if st.button("Torna al Login"):
            st.switch_page("main.py")

        st.stop()


# =========================
# LOGIN / LOGOUT
# =========================

def login_user():
    st.session_state["authenticated"] = True


def logout_user():
    st.session_state["authenticated"] = False


def logout_and_redirect():
    logout_user()
    st.switch_page("main.py")
``
