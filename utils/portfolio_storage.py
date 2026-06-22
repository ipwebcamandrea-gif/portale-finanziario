from __future__ import annotations

import base64
import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from utils.user_context import get_current_user
from utils.user_paths import (
    get_user_github_portfolio_path,
    get_user_portfolio_path,
)


PORTFOLIO_COLUMNS = [
    "ticker",
    "titolo",
    "mercato",
    "strumento",
    "valuta",
    "quantita",
    "prezzo_medio",
    "prezzo_mercato",
    "prezzo_precedente",
    "yf_symbol",
    "tv_symbol",
]

TEXT_COLUMNS = [
    "ticker",
    "titolo",
    "mercato",
    "strumento",
    "valuta",
    "yf_symbol",
    "tv_symbol",
]
NUMERIC_COLUMNS = ["quantita", "prezzo_medio", "prezzo_mercato", "prezzo_precedente"]

DEFAULT_PORTFOLIO_BRANCH = "data-watchlists"
DEFAULT_PORTFOLIO_JSON_PATH = "portfolio/portafoglio.json"


# =========================
# SECRETS / CONFIG
# =========================

def _secret_value(*names: str, default: str = "") -> str:
    """Read a top-level Streamlit secret, supporting multiple possible names."""
    for name in names:
        try:
            value = st.secrets.get(name, "")
            if value:
                return str(value).strip()
        except Exception:
            continue
    return default


def _github_secret_value(name: str, default: str = "") -> str:
    """Read a nested [github] Streamlit secret used by this project."""
    try:
        github_cfg = st.secrets.get("github", {})
        if github_cfg and name in github_cfg and github_cfg.get(name):
            return str(github_cfg.get(name)).strip()
    except Exception:
        pass
    return default


def _github_storage_enabled() -> bool:
    """Respect [github].use_github_storage when present.

    If the flag is absent, GitHub storage is considered enabled when token/repo
    are available, preserving compatibility with the flat-secrets format.
    """
    try:
        github_cfg = st.secrets.get("github", {})
        if github_cfg and "use_github_storage" in github_cfg:
            return bool(github_cfg.get("use_github_storage"))
    except Exception:
        pass
    return True


def get_portfolio_github_config(path_override: str | None = None) -> dict[str, str]:
    """Return GitHub configuration for portfolio persistence.

    Supports the project's nested secrets format:

    [github]
    token = "..."
    owner = "ipwebcamandrea-gif"
    repo = "portale-finanziario"
    branch = "data-watchlists"

    Also supports the previous flat format:

    GITHUB_TOKEN = "..."
    GITHUB_REPO = "owner/repo"
    """
    nested_token = _github_secret_value("token")
    nested_owner = _github_secret_value("owner")
    nested_repo_name = _github_secret_value("repo")
    nested_branch = _github_secret_value("branch", DEFAULT_PORTFOLIO_BRANCH)

    flat_token = _secret_value("GITHUB_TOKEN", "GH_TOKEN")
    flat_repo = _secret_value("GITHUB_REPO", "GITHUB_REPOSITORY")
    flat_branch = _secret_value("GITHUB_PORTFOLIO_BRANCH", default=DEFAULT_PORTFOLIO_BRANCH)

    token = nested_token or flat_token

    if nested_owner and nested_repo_name:
        repo = f"{nested_owner}/{nested_repo_name}"
    else:
        repo = flat_repo

    branch = _secret_value(
        "GITHUB_PORTFOLIO_BRANCH",
        default=(nested_branch or flat_branch or DEFAULT_PORTFOLIO_BRANCH),
    )

    try:
        user_portfolio_path = get_user_github_portfolio_path()
    except Exception:
        user_portfolio_path = DEFAULT_PORTFOLIO_JSON_PATH

    # Multiutenza: il path predefinito è sempre quello dell'utente corrente.
    # GITHUB_PORTFOLIO_PATH resta supportato solo come fallback se non esiste un utente in sessione.
    path = str(path_override or user_portfolio_path or DEFAULT_PORTFOLIO_JSON_PATH).strip().lstrip("/")

    return {
        "token": token,
        "repo": repo,
        "branch": branch,
        "path": path,
        "enabled": "true" if _github_storage_enabled() else "false",
    }


def is_github_configured() -> bool:
    cfg = get_portfolio_github_config()
    return bool(
        cfg.get("enabled") == "true"
        and cfg.get("token")
        and cfg.get("repo")
        and cfg.get("branch")
        and cfg.get("path")
    )


def set_portfolio_storage_state(mode: str, error: str = "") -> None:
    st.session_state["portfolio_storage_mode"] = mode
    st.session_state["portfolio_last_github_error"] = error
    try:
        cfg = get_portfolio_github_config()
        st.session_state["portfolio_storage_path"] = f"{cfg.get('branch', 'data-watchlists')}/{cfg.get('path', '')}"
    except Exception:
        try:
            st.session_state["portfolio_storage_path"] = str(get_user_portfolio_path())
        except Exception:
            st.session_state["portfolio_storage_path"] = DEFAULT_PORTFOLIO_JSON_PATH


# =========================
# NORMALIZZAZIONE DATI
# =========================

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_portfolio_file(json_path: Path) -> None:
    """Create the local portfolio JSON if it does not exist yet."""
    json_path.parent.mkdir(parents=True, exist_ok=True)

    if not json_path.exists():
        payload = {
            "version": 1,
            "updated_at": _utc_now_iso(),
            "positions": [],
        }
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    for col in PORTFOLIO_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[PORTFOLIO_COLUMNS].copy()

    for col in TEXT_COLUMNS:
        df[col] = df[col].fillna("").astype(str).str.strip()

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["ticker"] = df["ticker"].str.upper()
    df["mercato"] = df["mercato"].str.upper()
    df["valuta"] = df["valuta"].str.upper()
    df["yf_symbol"] = df["yf_symbol"].str.upper()
    df["tv_symbol"] = df["tv_symbol"].str.upper()

    return df


def _json_text_to_payload(json_text: str) -> dict[str, Any]:
    if not json_text.strip():
        return {"version": 1, "updated_at": _utc_now_iso(), "positions": []}

    payload = json.loads(json_text)

    if isinstance(payload, list):
        return {"version": 1, "updated_at": _utc_now_iso(), "positions": payload}

    if not isinstance(payload, dict):
        return {"version": 1, "updated_at": _utc_now_iso(), "positions": []}

    if "positions" not in payload:
        payload["positions"] = []

    return payload


def _payload_to_df(payload: dict[str, Any]) -> pd.DataFrame:
    positions = payload.get("positions", [])
    if not isinstance(positions, list):
        positions = []
    return _normalize_df(pd.DataFrame(positions))


def _df_to_payload(df: pd.DataFrame) -> dict[str, Any]:
    normalized = _normalize_df(df)
    return {
        "version": 1,
        "updated_at": _utc_now_iso(),
        "positions": normalized.to_dict(orient="records"),
    }


def _payload_to_json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _read_local_payload(json_path: Path) -> dict[str, Any]:
    ensure_portfolio_file(json_path)
    return _json_text_to_payload(json_path.read_text(encoding="utf-8"))


def _write_local_payload(json_path: Path, payload: dict[str, Any]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(_payload_to_json_text(payload), encoding="utf-8")


# =========================
# GITHUB API
# =========================

def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "portale-finanziario-portfolio-storage-json",
    }


def _github_contents_url(repo: str, path: str) -> str:
    clean_path = path.strip().lstrip("/")
    quoted_path = urllib.parse.quote(clean_path, safe="/")
    return f"https://api.github.com/repos/{repo}/contents/{quoted_path}"


def _github_get_file(path_override: str | None = None) -> dict[str, Any]:
    import requests

    cfg = get_portfolio_github_config(path_override=path_override)
    url = _github_contents_url(cfg["repo"], cfg["path"])
    response = requests.get(
        url,
        headers=_github_headers(cfg["token"]),
        params={"ref": cfg["branch"]},
        timeout=20,
    )

    if response.status_code == 404:
        return {"exists": False, "content": "", "sha": ""}

    response.raise_for_status()
    payload = response.json()
    encoded_content = payload.get("content", "")
    content = base64.b64decode(encoded_content).decode("utf-8") if encoded_content else ""
    return {"exists": True, "content": content, "sha": payload.get("sha", "")}


def _github_put_file(json_text: str, message: str, path_override: str | None = None) -> None:
    import requests

    cfg = get_portfolio_github_config(path_override=path_override)
    url = _github_contents_url(cfg["repo"], cfg["path"])
    current = _github_get_file(path_override=path_override)
    encoded_content = base64.b64encode(json_text.encode("utf-8")).decode("ascii")

    payload: dict[str, Any] = {
        "message": message,
        "content": encoded_content,
        "branch": cfg["branch"],
    }

    if current.get("exists") and current.get("sha"):
        payload["sha"] = current["sha"]

    response = requests.put(
        url,
        headers=_github_headers(cfg["token"]),
        json=payload,
        timeout=20,
    )
    response.raise_for_status()


# =========================
# API PUBBLICA
# =========================

def load_portfolio(json_path: Path) -> pd.DataFrame:
    """Load portfolio positions from the current user's GitHub/local JSON."""
    ensure_portfolio_file(json_path)

    if is_github_configured():
        try:
            remote = _github_get_file()

            if remote.get("exists"):
                payload = _json_text_to_payload(remote.get("content", ""))
                _write_local_payload(json_path, payload)
                set_portfolio_storage_state("github")
                return _payload_to_df(payload)

            # First access for this user: create users/<utente>/portafoglio.json.
            # Andrea receives a copy of the legacy GitHub portfolio if it exists;
            # all other users start from the already-created empty local payload.
            payload = None
            if get_current_user() == "andrea":
                legacy_remote = _github_get_file(path_override=DEFAULT_PORTFOLIO_JSON_PATH)
                if legacy_remote.get("exists"):
                    payload = _json_text_to_payload(legacy_remote.get("content", ""))

            if payload is None:
                payload = _read_local_payload(json_path)

            _write_local_payload(json_path, payload)
            _github_put_file(
                _payload_to_json_text(payload),
                "multiuser: crea portafoglio utente " + (get_current_user() or "unknown"),
            )
            set_portfolio_storage_state("github")
            return _payload_to_df(payload)
        except Exception as exc:
            set_portfolio_storage_state("locale_fallback", str(exc))
    else:
        cfg = get_portfolio_github_config()
        if cfg.get("enabled") != "true":
            set_portfolio_storage_state("locale", "[github].use_github_storage è false")
        else:
            set_portfolio_storage_state("locale", "Configurazione GitHub incompleta")

    return _payload_to_df(_read_local_payload(json_path))


def save_portfolio(
    df: pd.DataFrame,
    json_path: Path,
    commit_message: str = "Update portfolio JSON from Streamlit app",
) -> None:
    """Persist portfolio positions locally and, when configured, to GitHub JSON."""
    payload = _df_to_payload(df)
    _write_local_payload(json_path, payload)

    if is_github_configured():
        try:
            _github_put_file(_payload_to_json_text(payload), commit_message)
            set_portfolio_storage_state("github")
            return
        except Exception as exc:
            set_portfolio_storage_state("locale_fallback", str(exc))
            return

    cfg = get_portfolio_github_config()
    if cfg.get("enabled") != "true":
        set_portfolio_storage_state("locale", "[github].use_github_storage è false")
    else:
        set_portfolio_storage_state("locale", "Configurazione GitHub incompleta")


def add_position(json_path: Path, position: dict) -> None:
    """Append a new portfolio position."""
    df = load_portfolio(json_path)
    new_row = {col: position.get(col, "") for col in PORTFOLIO_COLUMNS}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_portfolio(df, json_path, "Add portfolio position")


def update_position(json_path: Path, row_index: int, position: dict) -> None:
    """Update a portfolio position by original JSON row index."""
    df = load_portfolio(json_path)

    if row_index < 0 or row_index >= len(df):
        return

    for col in PORTFOLIO_COLUMNS:
        if col in position:
            df.at[row_index, col] = position[col]

    save_portfolio(df, json_path, "Update portfolio position")


def delete_position(json_path: Path, row_index: int) -> None:
    """Delete a portfolio position by original JSON row index."""
    df = load_portfolio(json_path)

    if row_index < 0 or row_index >= len(df):
        return

    df = df.drop(index=row_index).reset_index(drop=True)
    save_portfolio(df, json_path, "Delete portfolio position")
