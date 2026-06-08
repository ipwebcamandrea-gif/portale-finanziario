import streamlit as st
from pathlib import Path


# =========================
# CONFIGURAZIONE PAGINA
# =========================

st.set_page_config(
    page_title="FinancePortal 2026",
    page_icon="📊",
    layout="centered"
)


# =========================
# CONFIGURAZIONE FILE / CSS
# =========================

ROOT_DIR = Path(__file__).resolve().parent
GLOBAL_CSS = ROOT_DIR / "css" / "global.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(
                f"<style>{file.read()}</style>",
                unsafe_allow_html=True
            )


local_css(GLOBAL_CSS)


# =========================
# SESSION STATE
# =========================

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False


# =========================
# CREDENZIALI
# =========================

def get_admin_password():
    """
    Legge la password admin dai Secrets di Streamlit.

    Formato consigliato nei Secrets:

    [credentials.usernames]
    admin = "LA_TUA_PASSWORD"
    """
    try:
        return st.secrets["credentials"]["usernames"]["admin"]
    except Exception:
        return None


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = get_admin_password()


# =========================
# SE GIÀ AUTENTICATO
# =========================

if st.session_state.get("authenticated", False):
    st.switch_page("pages/dashboard.py")


# =========================
# INTERFACCIA LOGIN
# =========================

st.markdown(
    '<div class="hero-title">FinancePortal 2026</div>',
    unsafe_allow_html=True
)

with st.container():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)

    st.subheader("Accedi al sistema")

    with st.form("login_form"):
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Entra nella Dashboard")

        if submitted:
            if ADMIN_PASSWORD is None:
                st.session_state["authenticated"] = False
                st.error(
                    "Password admin non configurata nei Secrets di Streamlit."
                )

            elif user.strip() == ADMIN_USERNAME and password.strip() == ADMIN_PASSWORD:
                st.session_state["authenticated"] = True
                st.switch_page("pages/dashboard.py")

            else:
                st.session_state["authenticated"] = False
                st.error("Credenziali non valide")

    st.markdown("</div>", unsafe_allow_html=True)
