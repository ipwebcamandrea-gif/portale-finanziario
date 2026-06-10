import json
from pathlib import Path

import streamlit as st

try:
    from utils.github_storage import (
        github_storage_enabled,
        read_watchlists_from_github,
        write_watchlists_to_github,
    )
except Exception:
    def github_storage_enabled():
        return False

    def read_watchlists_from_github():
        raise RuntimeError("Modulo github_storage non disponibile.")

    def write_watchlists_to_github(data, previous_sha=None, commit_message=None):
        raise RuntimeError("Modulo github_storage non disponibile.")


# =========================
# CONFIGURAZIONE STORAGE
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent
WATCHLISTS_JSON = ROOT_DIR / "watchlists.json"


# =========================
# DEFAULT DATA
# =========================

DEFAULT_DATA = {
    "version": 1,
    "active_watchlist": "Default",
    "watchlists": {
        "Default": ["AAPL", "MSFT", "GOOGL"],
        "Finanza": ["JPM", "BAC", "V", "MA"],
        "ETF": ["SWDA.MI", "EIMI.MI"]
    }
}


# =========================
# PERSISTENZA JSON + GITHUB
# =========================

def copia_default_data():
    return json.loads(json.dumps(DEFAULT_DATA))


def normalizza_dati_watchlists(data):
    if not isinstance(data, dict):
        return copia_default_data()

    if "watchlists" not in data or not isinstance(data["watchlists"], dict):
        if all(isinstance(value, list) for value in data.values()):
            data = {
                "version": 1,
                "active_watchlist": list(data.keys())[0] if data else "Default",
                "watchlists": data
            }
        else:
            return copia_default_data()

    if "version" not in data:
        data["version"] = 1

    watchlists = data.get("watchlists", {})

    if not watchlists:
        watchlists = {"Default": []}
        data["watchlists"] = watchlists

    watchlists_pulite = {}

    for nome_lista, simboli in watchlists.items():
        nome_pulito = str(nome_lista).strip()

        if not nome_pulito:
            continue

        if not isinstance(simboli, list):
            simboli = []

        simboli_puliti = []

        for simbolo in simboli:
            simbolo_pulito = str(simbolo).strip().upper()

            if simbolo_pulito and simbolo_pulito not in simboli_puliti:
                simboli_puliti.append(simbolo_pulito)

        watchlists_pulite[nome_pulito] = simboli_puliti

    if not watchlists_pulite:
        watchlists_pulite = {"Default": []}

    data["watchlists"] = watchlists_pulite

    active = data.get("active_watchlist")

    if active not in watchlists_pulite:
        data["active_watchlist"] = list(watchlists_pulite.keys())[0]

    return data


def salva_watchlists_locale(data):
    data = normalizza_dati_watchlists(data)

    with open(WATCHLISTS_JSON, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def carica_watchlists_da_json():
    if github_storage_enabled():
        try:
            data, sha = read_watchlists_from_github()
            data = normalizza_dati_watchlists(data)
            st.session_state["tv_github_watchlists_sha"] = sha
            st.session_state["tv_storage_mode"] = "github"
            st.session_state["tv_last_github_error"] = ""
            salva_watchlists_locale(data)
            return data
        except Exception as error:
            st.session_state["tv_storage_mode"] = "locale_fallback"
            st.session_state["tv_last_github_error"] = str(error)

    if not WATCHLISTS_JSON.exists():
        salva_watchlists_locale(copia_default_data())
        return copia_default_data()

    try:
        with open(WATCHLISTS_JSON, "r", encoding="utf-8") as file:
            data = json.load(file)
        return normalizza_dati_watchlists(data)
    except Exception:
        return copia_default_data()


def salva_watchlists_su_json(data):
    data = normalizza_dati_watchlists(data)
    salva_watchlists_locale(data)

    if github_storage_enabled():
        try:
            previous_sha = st.session_state.get("tv_github_watchlists_sha")
            response = write_watchlists_to_github(
                data,
                previous_sha=previous_sha,
                commit_message="update: aggiorna watchlists.json da Streamlit"
            )
            new_sha = response.get("content", {}).get("sha")
            if new_sha:
                st.session_state["tv_github_watchlists_sha"] = new_sha
            st.session_state["tv_storage_mode"] = "github"
            st.session_state["tv_last_github_save_ok"] = True
            st.session_state["tv_last_github_error"] = ""
        except Exception as error:
            st.session_state["tv_storage_mode"] = "locale_fallback"
            st.session_state["tv_last_github_save_ok"] = False
            st.session_state["tv_last_github_error"] = str(error)


def aggiorna_sessione_da_disco():
    st.session_state["tv_watchlists_data"] = carica_watchlists_da_json()
    st.session_state["tv_current_list"] = st.session_state["tv_watchlists_data"].get(
        "active_watchlist",
        list(st.session_state["tv_watchlists_data"]["watchlists"].keys())[0]
    )


def salva_sessione_su_disco():
    data = st.session_state["tv_watchlists_data"]
    data["active_watchlist"] = st.session_state.get("tv_current_list")
    salva_watchlists_su_json(data)
