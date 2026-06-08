import streamlit as st
from pathlib import Path


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

st.session_state["authenticated"] = False

chiavi_da_rimuovere = [
    "ticker_selezionato",
    "lista_tickers"
]

for chiave in chiavi_da_rimuovere:
    if chiave in st.session_state:
        del st.session_state[chiave]


# =========================
# INTERFACCIA
# =========================

st.markdown(
    """
    <div class="hero-title">Sessione terminata</div>
    """,
    unsafe_allow_html=True
)

st.success("Logout effettuato correttamente.")

st.info(
    "La sessione è stata chiusa. "
    "Per continuare, torna alla pagina di login."
)

if st.button("Torna al Login"):
    st.switch_page("main.py")
