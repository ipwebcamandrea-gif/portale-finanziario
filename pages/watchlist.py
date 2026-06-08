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
WATCHLIST_FILE = ROOT_DIR / "watchlist.txt"

GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
WATCHLIST_CSS = ROOT_DIR / "css" / "watchlist.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(
                f"<style>{file.read()}</style>",
                unsafe_allow_html=True
            )


local_css(GLOBAL_CSS)
local_css(WATCHLIST_CSS)


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


def rimuovi_duplicati(lista_ticker):
    lista_pulita = []

    for ticker in lista_ticker:
        ticker_pulito = ticker.strip().upper()

        if ticker_pulito and ticker_pulito not in lista_pulita:
            lista_pulita.append(ticker_pulito)

    return lista_pulita


def identifica_mercato(ticker):
    ticker = ticker.upper().strip()

    if ticker.endswith(".MI"):
        return {
            "label": "Italia",
            "classe": "market-italy"
        }

    if "." not in ticker:
        return {
            "label": "USA",
            "classe": "market-usa"
        }

    return {
        "label": "Altro",
        "classe": "market-other"
    }


# =========================
# INIZIALIZZAZIONE SESSIONE
# =========================

if "lista_tickers" not in st.session_state:
    st.session_state["lista_tickers"] = rimuovi_duplicati(
        carica_watchlist()
    )


# =========================
# HEADER
# =========================

st.markdown(
    """
    <div class="watchlist-header">
        <div class="watchlist-title">Gestione Watchlist</div>
        <div class="watchlist-subtitle">
            Aggiungi, rimuovi e controlla i ticker usati dalla Dashboard.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# PANNELLO AGGIUNTA
# =========================

st.markdown(
    """
    <div class="watchlist-panel">
        <div class="watchlist-panel-title">Aggiungi nuovo ticker</div>
        <div class="watchlist-panel-subtitle">
            Inserisci il simbolo Yahoo Finance. Esempi: AAPL, NVDA, SWDA.MI, ENI.MI.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

with st.form("add_ticker_form"):
    nuovo_ticker = st.text_input(
        "Ticker",
        placeholder="Esempio: AAPL, NVDA, SWDA.MI"
    )

    submitted = st.form_submit_button("Aggiungi alla watchlist")

    if submitted:
        ticker_pulito = nuovo_ticker.strip().upper()

        if not ticker_pulito:
            st.warning("Inserisci un ticker valido.")

        elif ticker_pulito in st.session_state["lista_tickers"]:
            st.warning(f"{ticker_pulito} è già presente nella watchlist.")

        else:
            st.session_state["lista_tickers"].append(ticker_pulito)
            st.session_state["lista_tickers"] = rimuovi_duplicati(
                st.session_state["lista_tickers"]
            )
            salva_watchlist(st.session_state["lista_tickers"])
            st.success(f"{ticker_pulito} aggiunto alla watchlist.")
            st.rerun()


# =========================
# LISTA TICKER
# =========================

st.markdown(
    """
    <div class="watchlist-list-card">
        <div class="watchlist-list-title">Ticker presenti</div>
    </div>
    """,
    unsafe_allow_html=True
)

if not st.session_state["lista_tickers"]:
    st.markdown(
        """
        <div class="watchlist-empty">
            La watchlist è vuota. Aggiungi almeno un ticker per iniziare.
        </div>
        """,
        unsafe_allow_html=True
    )

else:
    for ticker in list(st.session_state["lista_tickers"]):
        mercato = identifica_mercato(ticker)

        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(
                f"""
                <div class="watchlist-row">
                    <div class="watchlist-ticker-symbol">{ticker}</div>
                    <div class="watchlist-ticker-note">
                        Simbolo usato da Yahoo Finance
                    </div>
                    <span class="market-badge {mercato["classe"]}">
                        {mercato["label"]}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            if st.button("🗑️", key=f"remove_{ticker}"):
                st.session_state["lista_tickers"].remove(ticker)
                salva_watchlist(st.session_state["lista_tickers"])
                st.rerun()


# =========================
# NAVIGAZIONE
# =========================

st.markdown("---")

col_back, col_dashboard = st.columns([1, 3])

with col_back:
    if st.button("⬅️ Dashboard"):
        st.switch_page("pages/dashboard.py")
