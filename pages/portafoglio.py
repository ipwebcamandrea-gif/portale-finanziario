import streamlit as st
from pathlib import Path


# =========================
# PROTEZIONE LOGIN
# =========================

if not st.session_state.get("authenticated", False):
    st.error("Accesso non autorizzato.")

    if st.button("Torna al Login"):
        st.switch_page("main.py")

    st.stop()


# =========================
# CONFIGURAZIONE FILE / CSS
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent

GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
PORTAFOGLIO_CSS = ROOT_DIR / "css" / "portafoglio.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(
                f"<style>{file.read()}</style>",
                unsafe_allow_html=True
            )


local_css(GLOBAL_CSS)
local_css(PORTAFOGLIO_CSS)


# =========================
# HEADER
# =========================

st.markdown(
    """
    <div class="portafoglio-header">
        <div class="portafoglio-title">Il Mio Portafoglio</div>
        <div class="portafoglio-subtitle">
            Area dedicata al monitoraggio delle posizioni reali.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# PANNELLO INFORMATIVO
# =========================

st.markdown(
    """
    <div class="portafoglio-panel">
        <div class="portafoglio-panel-title">Modulo in preparazione</div>
        <div class="portafoglio-panel-subtitle">
            Questa sezione è pronta per essere sviluppata nella prossima fase.
            Qui potremo inserire quantità, prezzo medio di carico, valore attuale,
            profit/loss, peso in portafoglio e suddivisione per asset.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# KPI PLACEHOLDER
# =========================

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

with kpi_1:
    st.markdown(
        """
        <div class="portafoglio-kpi-card">
            <div class="portafoglio-kpi-label">Valore totale</div>
            <div class="portafoglio-kpi-value">N/D</div>
            <div class="portafoglio-kpi-note">In sviluppo</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with kpi_2:
    st.markdown(
        """
        <div class="portafoglio-kpi-card">
            <div class="portafoglio-kpi-label">Profit/Loss</div>
            <div class="portafoglio-kpi-value">N/D</div>
            <div class="portafoglio-kpi-note">In sviluppo</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with kpi_3:
    st.markdown(
        """
        <div class="portafoglio-kpi-card">
            <div class="portafoglio-kpi-label">Posizioni</div>
            <div class="portafoglio-kpi-value">N/D</div>
            <div class="portafoglio-kpi-note">In sviluppo</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with kpi_4:
    st.markdown(
        """
        <div class="portafoglio-kpi-card">
            <div class="portafoglio-kpi-label">Esposizione</div>
            <div class="portafoglio-kpi-value">N/D</div>
            <div class="portafoglio-kpi-note">In sviluppo</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# PLACEHOLDER FUNZIONALE
# =========================

st.markdown(
    """
    <div class="portafoglio-placeholder">
        <div class="placeholder-title">Prossimo sviluppo: portafoglio reale</div>
        <div class="placeholder-text">
            Nella prossima versione potremo aggiungere un file dedicato, ad esempio
            <strong>portfolio.csv</strong>, con ticker, quantità, prezzo medio,
            valuta e categoria. Da quei dati la pagina potrà calcolare valore attuale,
            performance e allocazione.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# NAVIGAZIONE
# =========================

st.markdown("---")

if st.button("⬅️ Torna alla Dashboard"):
    st.switch_page("pages/dashboard.py")
