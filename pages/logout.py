import streamlit as st
from pathlib import Path

from utils.auth import logout_user
from utils.user_context import get_current_user_display_name


# =========================
# CONFIGURAZIONE FILE / CSS
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent

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
# LOGOUT
# =========================

logged_out_user_display_name = get_current_user_display_name("utente")
logout_user()


# =========================
# INTERFACCIA
# =========================

st.markdown(
    """
    <div class="hero-title">Sessione terminata</div>
    """,
    unsafe_allow_html=True
)

st.success(f"Logout effettuato correttamente per {logged_out_user_display_name}.")

st.info(
    "La sessione è stata chiusa. "
    "Per continuare, torna alla pagina di login."
)

if st.button("Torna al Login"):
    st.switch_page("main.py")
