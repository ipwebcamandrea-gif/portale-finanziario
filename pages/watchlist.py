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
# CONFIGURAZIONE FILE
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent
WATCHLIST_FILE = ROOT_DIR / "watchlist.txt"


# =========================
# FUNZIONI WATCHLIST
# =========================

def carica_watchlist():
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as file:
            return [
                line.strip().upper()
                for line in file.readlines()
                if line.strip()
            ]

    return ["AAPL", "TSLA", "NVDA"]


def salva_watchlist(lista_ticker):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as file:
        for ticker in lista_ticker:
            file.write(f"{ticker}\n")


# =========================
# INIZIALIZZAZIONE SESSIONE
# =========================

if "lista_tickers" not in st.session_state:
    st.session_state["lista_tickers"] = carica_watchlist()


# =========================
# INTERFACCIA
# =========================

st.title("📊 La mia Watchlist")

st.write(
    "Da questa pagina puoi aggiungere o rimuovere ticker. "
    "La lista è la stessa usata dalla Dashboard."
)


# =========================
# FORM AGGIUNTA TICKER
# =========================

with st.form("add_ticker_form"):
    nuovo_ticker = st.text_input(
        "Inserisci simbolo ticker",
        placeholder="Esempio: AAPL, NVDA, SWDA.MI"
    )

    submitted = st.form_submit_button("Aggiungi alla lista")

    if submitted:
        ticker_pulito = nuovo_ticker.strip().upper()

        if not ticker_pulito:
            st.warning("Inserisci un ticker valido.")

        elif ticker_pulito in st.session_state["lista_tickers"]:
            st.warning(f"{ticker_pulito} è già presente nella watchlist.")

        else:
            st.session_state["lista_tickers"].append(ticker_pulito)
            salva_watchlist(st.session_state["lista_tickers"])
            st.success(f"{ticker_pulito} aggiunto alla watchlist.")
            st.rerun()


# =========================
# VISUALIZZAZIONE LISTA
# =========================

st.subheader("Ticker presenti")

if not st.session_state["lista_tickers"]:
    st.info("La watchlist è vuota.")
else:
    for ticker in list(st.session_state["lista_tickers"]):
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"**{ticker}**")

        with col2:
            if st.button("🗑️", key=f"remove_{ticker}"):
                st.session_state["lista_tickers"].remove(ticker)
                salva_watchlist(st.session_state["lista_tickers"])
                st.rerun()

        st.divider()


# =========================
# NAVIGAZIONE
# =========================

if st.button("⬅️ Torna alla Dashboard"):
    st.switch_page("pages/dashboard.py")
