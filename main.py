import streamlit as st
from pathlib import Path
from utils.app_branding import get_app_icon

from utils.auth import (
    is_authenticated,
    login_user,
    logout_user,
)


# =========================
# CONFIGURAZIONE PAGINA
# =========================

st.set_page_config(
    page_title="FinancePortal 2026",
    page_icon=get_app_icon(),
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
# CSS INLINE LOGIN SPECIFICO
# =========================

st.markdown(
    """
    <style>
    div[class*="st-key-login_card"] {
        max-width: 460px;
        margin: 0 auto;
        padding: 2.2rem 2.4rem 2.3rem 2.4rem;
        border-radius: 16px;
        border: 1px solid rgba(48, 54, 61, 0.92);
        background:
            radial-gradient(circle at top right, rgba(0, 176, 255, 0.13), transparent 36%),
            linear-gradient(135deg, rgba(22, 27, 34, 0.98) 0%, rgba(13, 17, 23, 0.98) 100%);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.04),
            0 0 24px rgba(0, 176, 255, 0.08);
    }

    div[class*="st-key-login_card"] h3 {
        text-align: center;
        margin-top: 0;
        margin-bottom: 1.1rem;
    }

    div[class*="st-key-login_card"] .stButton > button,
    div[class*="st-key-login_card"] [data-testid="stFormSubmitButton"] > button {
        min-height: 40px;
        border-radius: 10px;
        font-weight: 900;
        border-color: rgba(0, 176, 255, 0.56);
        background:
            radial-gradient(circle at top left, rgba(0, 176, 255, 0.22), transparent 36%),
            linear-gradient(135deg, rgba(0, 176, 255, 0.15) 0%, rgba(22, 27, 34, 0.95) 100%);
    }

    div[class*="st-key-login_card"] .stButton > button:hover,
    div[class*="st-key-login_card"] [data-testid="stFormSubmitButton"] > button:hover {
        border-color: rgba(0, 176, 255, 0.88);
        box-shadow: 0 0 18px rgba(0, 176, 255, 0.18);
        transform: translateY(-1px);
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================
# SESSION STATE
# =========================

if "authenticated" not in st.session_state:
    logout_user()


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

if is_authenticated():
    st.switch_page("pages/dashboard.py")


# =========================
# INTERFACCIA LOGIN
# =========================

st.markdown(
    '<div class="hero-title">FinancePortal 2026</div>',
    unsafe_allow_html=True
)

with st.container(key="login_card"):
    st.subheader("Accedi al sistema")

    with st.form("login_form"):
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Entra nella Dashboard")

        if submitted:
            if ADMIN_PASSWORD is None:
                logout_user()
                st.error(
                    "Password admin non configurata nei Secrets di Streamlit."
                )

            elif user.strip() == ADMIN_USERNAME and password.strip() == ADMIN_PASSWORD:
                login_user()
                st.switch_page("pages/dashboard.py")

            else:
                logout_user()
                st.error("Credenziali non valide")
