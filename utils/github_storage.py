import base64
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

import streamlit as st


# =========================
# GITHUB STORAGE CONFIG
# =========================

class GitHubStorageError(RuntimeError):
    """Errore GitHub API con status code disponibile."""

    def __init__(self, message, status_code=None, response_body=""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def github_storage_enabled():
    """True se la persistenza GitHub è abilitata nei Secrets Streamlit."""
    try:
        return bool(st.secrets.get("github", {}).get("use_github_storage", False))
    except Exception:
        return False


def get_github_config():
    """Legge la configurazione GitHub dai Secrets Streamlit."""
    github = st.secrets.get("github", {})

    token = github.get("token", "")
    owner = github.get("owner", "")
    repo = github.get("repo", "")
    branch = github.get("branch", "data-watchlists")
    watchlists_path = github.get("watchlists_path", "watchlists.json")

    if not token or not owner or not repo or not branch or not watchlists_path:
        raise ValueError("Configurazione GitHub incompleta nei Secrets Streamlit.")

    return {
        "token": token,
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "watchlists_path": watchlists_path,
    }


def github_api_url(config):
    owner = config["owner"]
    repo = config["repo"]
    path = config["watchlists_path"].lstrip("/")
    return f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"


def github_headers(config):
    return {
        "Authorization": "Bearer " + config["token"],
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "streamlit-watchlists-storage",
    }


def github_request(method, url, config, payload=None):
    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=github_headers(config),
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_text = response.read().decode("utf-8")
            if not response_text:
                return {}
            return json.loads(response_text)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise GitHubStorageError(
            f"GitHub API error {error.code}: {error_body}",
            status_code=error.code,
            response_body=error_body,
        ) from error

    except urllib.error.URLError as error:
        raise GitHubStorageError(f"Errore connessione GitHub API: {error}") from error


# =========================
# READ / WRITE WATCHLISTS
# =========================

def read_watchlists_from_github():
    """
    Legge watchlists.json dal branch dati GitHub.

    Ritorna:
    - data: dict JSON
    - sha: SHA del file GitHub, necessario per aggiornamenti successivi
    """
    config = get_github_config()
    url = github_api_url(config) + "?ref=" + config["branch"]

    response = github_request("GET", url, config)

    content_base64 = response.get("content", "")
    sha = response.get("sha", "")

    if not content_base64 or not sha:
        raise RuntimeError("Risposta GitHub non valida: contenuto o SHA mancanti.")

    content_clean = content_base64.replace("\n", "")
    decoded = base64.b64decode(content_clean).decode("utf-8")
    data = json.loads(decoded)

    return data, sha


def _write_watchlists_to_github_once(config, data, previous_sha, commit_message):
    """Esegue un singolo tentativo di scrittura su GitHub usando lo SHA indicato."""
    json_text = json.dumps(data, indent=4, ensure_ascii=False)
    encoded_content = base64.b64encode(json_text.encode("utf-8")).decode("utf-8")

    payload = {
        "message": commit_message,
        "content": encoded_content,
        "sha": previous_sha,
        "branch": config["branch"],
    }

    return github_request("PUT", github_api_url(config), config, payload)


def write_watchlists_to_github(data, previous_sha=None, commit_message=None, retry_on_sha_conflict=True):
    """
    Scrive watchlists.json sul branch dati GitHub creando un commit.

    Se previous_sha non viene passato, viene letto prima lo SHA attuale del file.

    Gestione errore 409:
    - GitHub restituisce 409 quando lo SHA usato non corrisponde più alla versione attuale del file.
    - In quel caso questa funzione rilegge lo SHA aggiornato e riprova una sola volta.
    - Questo rende robusti i salvataggi ravvicinati da Streamlit.
    """
    config = get_github_config()

    if previous_sha is None:
        _, previous_sha = read_watchlists_from_github()

    if commit_message is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        commit_message = f"update: aggiorna watchlists.json ({timestamp})"

    try:
        return _write_watchlists_to_github_once(config, data, previous_sha, commit_message)

    except GitHubStorageError as error:
        is_sha_conflict = error.status_code == 409

        if not retry_on_sha_conflict or not is_sha_conflict:
            raise

        # Lo SHA locale è vecchio: rileggo lo SHA corrente da GitHub e riprovo una volta.
        _, fresh_sha = read_watchlists_from_github()
        retry_message = commit_message + " [retry sha aggiornata]"
        return _write_watchlists_to_github_once(config, data, fresh_sha, retry_message)


def test_github_storage_connection():
    """
    Test leggero: prova a leggere watchlists.json da GitHub.
    Utile per verificare token, repo, branch e path.
    """
    data, sha = read_watchlists_from_github()
    return {
        "ok": True,
        "sha": sha,
        "watchlists_count": len(data.get("watchlists", {})) if isinstance(data, dict) else 0,
        "active_watchlist": data.get("active_watchlist") if isinstance(data, dict) else None,
    }
