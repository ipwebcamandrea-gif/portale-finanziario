import json
from pathlib import Path

import streamlit as st

from utils.user_context import get_current_user
from utils.user_paths import (
    get_legacy_watchlists_path,
    get_user_github_watchlists_display_path,
    get_user_github_watchlists_path,
    get_user_watchlists_path,
)

try:
    from utils.github_storage import (
        GitHubStorageError,
        github_storage_enabled,
        read_watchlists_from_github,
        write_watchlists_to_github,
    )
except Exception:
    class GitHubStorageError(RuntimeError):
        def __init__(self, message, status_code=None, response_body=""):
            super().__init__(message)
            self.status_code = status_code
            self.response_body = response_body

    def github_storage_enabled():
        return False

    def read_watchlists_from_github(watchlists_path=None):
        raise RuntimeError("Modulo github_storage non disponibile.")

    def write_watchlists_to_github(
        data,
        previous_sha=None,
        commit_message=None,
        retry_on_sha_conflict=True,
        watchlists_path=None,
    ):
        raise RuntimeError("Modulo github_storage non disponibile.")


# =========================
# CONFIGURAZIONE STORAGE
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent
WATCHLISTS_JSON = ROOT_DIR / "watchlists.json"  # legacy fallback only
MIGRATION_SOURCE_USER = "andrea"


# =========================
# DEFAULT DATA
# =========================

DEFAULT_DATA = {
    "version": 1,
    "active_watchlist": "Default",
    "watchlists": {
        "Default": []
    }
}


# =========================
# PERSISTENZA JSON + GITHUB
# =========================

def _current_user_id() -> str:
    return get_current_user() or "default"


def _current_local_watchlists_path() -> Path:
    try:
        return get_user_watchlists_path()
    except Exception:
        return WATCHLISTS_JSON


def _current_github_watchlists_path() -> str:
    try:
        return get_user_github_watchlists_path()
    except Exception:
        return "watchlists.json"


def _current_github_display_path() -> str:
    try:
        return get_user_github_watchlists_display_path()
    except Exception:
        return "data-watchlists/watchlists.json"


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
    json_path = _current_local_watchlists_path()
    json_path.parent.mkdir(parents=True, exist_ok=True)

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def _carica_watchlists_locale():
    json_path = _current_local_watchlists_path()

    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as file:
            return normalizza_dati_watchlists(json.load(file))

    # Safety fallback: for Andrea, if local user file is missing, copy legacy local data.
    legacy_path = get_legacy_watchlists_path()
    if _current_user_id() == MIGRATION_SOURCE_USER and legacy_path.exists():
        with open(legacy_path, "r", encoding="utf-8") as file:
            data = normalizza_dati_watchlists(json.load(file))
    else:
        data = copia_default_data()

    salva_watchlists_locale(data)
    return data


def _create_or_migrate_github_user_watchlists(user_path: str):
    """Create user Watchlist file on GitHub, copying Andrea legacy data when possible."""
    data = None

    if _current_user_id() == MIGRATION_SOURCE_USER:
        try:
            legacy_data, _legacy_sha = read_watchlists_from_github()
            data = normalizza_dati_watchlists(legacy_data)
        except Exception:
            data = None

    if data is None:
        data = copia_default_data()

    response = write_watchlists_to_github(
        data,
        previous_sha=None,
        commit_message="multiuser: crea watchlists utente " + _current_user_id(),
        watchlists_path=user_path,
    )
    sha = ""
    try:
        sha = response.get("content", {}).get("sha", "") if isinstance(response, dict) else ""
    except Exception:
        sha = ""

    return data, sha


def carica_watchlists_da_json():
    user_path = _current_github_watchlists_path()

    if github_storage_enabled():
        try:
            data, sha = read_watchlists_from_github(watchlists_path=user_path)
            data = normalizza_dati_watchlists(data)
            st.session_state["tv_github_watchlists_sha"] = sha
            st.session_state["tv_github_watchlists_path"] = user_path
            st.session_state["tv_storage_path"] = _current_github_display_path()
            st.session_state["tv_storage_mode"] = "github"
            st.session_state["tv_last_github_error"] = ""
            salva_watchlists_locale(data)
            return data

        except GitHubStorageError as errore:
            if getattr(errore, "status_code", None) == 404:
                try:
                    data, sha = _create_or_migrate_github_user_watchlists(user_path)
                    data = normalizza_dati_watchlists(data)
                    st.session_state["tv_github_watchlists_sha"] = sha
                    st.session_state["tv_github_watchlists_path"] = user_path
                    st.session_state["tv_storage_path"] = _current_github_display_path()
                    st.session_state["tv_storage_mode"] = "github"
                    st.session_state["tv_last_github_error"] = ""
                    salva_watchlists_locale(data)
                    return data
                except Exception as create_error:
                    st.session_state["tv_storage_mode"] = "locale_fallback"
                    st.session_state["tv_last_github_error"] = str(create_error)
                    return _carica_watchlists_locale()

            st.session_state["tv_storage_mode"] = "locale_fallback"
            st.session_state["tv_last_github_error"] = str(errore)
            return _carica_watchlists_locale()

        except Exception as errore:
            st.session_state["tv_storage_mode"] = "locale_fallback"
            st.session_state["tv_last_github_error"] = str(errore)
            return _carica_watchlists_locale()

    st.session_state["tv_storage_mode"] = "locale"
    st.session_state["tv_storage_path"] = str(_current_local_watchlists_path())
    return _carica_watchlists_locale()


def salva_watchlists_su_json(data):
    data = normalizza_dati_watchlists(data)
    salva_watchlists_locale(data)

    user_path = _current_github_watchlists_path()

    if github_storage_enabled():
        try:
            previous_sha = st.session_state.get("tv_github_watchlists_sha")
            response = write_watchlists_to_github(
                data,
                previous_sha=previous_sha,
                commit_message="update: aggiorna watchlists utente " + _current_user_id(),
                watchlists_path=user_path,
            )

            try:
                new_sha = response.get("content", {}).get("sha", "")
                if new_sha:
                    st.session_state["tv_github_watchlists_sha"] = new_sha
            except Exception:
                pass

            st.session_state["tv_github_watchlists_path"] = user_path
            st.session_state["tv_storage_path"] = _current_github_display_path()
            st.session_state["tv_storage_mode"] = "github"
            st.session_state["tv_last_github_error"] = ""

        except Exception as errore:
            st.session_state["tv_storage_mode"] = "locale_fallback"
            st.session_state["tv_last_github_error"] = str(errore)


def aggiorna_sessione_da_disco():
    st.session_state["tv_watchlists_data"] = carica_watchlists_da_json()

    current = st.session_state["tv_watchlists_data"].get("active_watchlist")
    watchlists = st.session_state["tv_watchlists_data"].get("watchlists", {})

    if current not in watchlists:
        current = list(watchlists.keys())[0]
        st.session_state["tv_watchlists_data"]["active_watchlist"] = current

    st.session_state["tv_current_list"] = current


def salva_sessione_su_disco():
    if "tv_watchlists_data" in st.session_state:
        data = st.session_state["tv_watchlists_data"]
        data["active_watchlist"] = st.session_state.get(
            "tv_current_list",
            data.get("active_watchlist", "Default")
        )
        salva_watchlists_su_json(data)
