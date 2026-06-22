from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from utils.portfolio_storage import get_portfolio_github_config
from utils.user_context import get_current_user
from utils.user_paths import get_user_github_targets_path, get_user_targets_path


DEFAULT_TARGET_BRANCH = "data-watchlists"
DEFAULT_TARGET_JSON_PATH = "portfolio/target_analisti.json"  # legacy fallback / migration source


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_payload() -> dict[str, Any]:
    return {"version": 1, "updated_at": utc_now_iso(), "targets": {}}


def normalize_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return default_payload()
    targets = payload.get("targets", {})
    if not isinstance(targets, dict):
        targets = {}
    return {
        "version": int(payload.get("version", 1) or 1),
        "updated_at": str(payload.get("updated_at") or utc_now_iso()),
        "targets": targets,
    }


def _key(yf_symbol: str) -> str:
    return str(yf_symbol or "").strip().upper()


def ensure_target_file(json_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    if not json_path.exists():
        json_path.write_text(json.dumps(default_payload(), indent=4, ensure_ascii=False), encoding="utf-8")


def _read_local(json_path: Path) -> dict[str, Any]:
    ensure_target_file(json_path)
    try:
        return normalize_payload(json.loads(json_path.read_text(encoding="utf-8")))
    except Exception:
        return default_payload()


def _write_local(json_path: Path, payload: dict[str, Any]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = normalize_payload(payload)
    payload["updated_at"] = utc_now_iso()
    json_path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")


def _current_targets_path() -> str:
    try:
        return get_user_github_targets_path()
    except Exception:
        return DEFAULT_TARGET_JSON_PATH


def _github_config(path_override: str | None = None) -> dict[str, str]:
    cfg = get_portfolio_github_config()
    path = str(path_override or _current_targets_path() or DEFAULT_TARGET_JSON_PATH).strip().lstrip("/")
    return {
        "token": cfg.get("token", ""),
        "repo": cfg.get("repo", ""),
        "branch": cfg.get("branch") or DEFAULT_TARGET_BRANCH,
        "path": path,
        "enabled": cfg.get("enabled", "false"),
    }


def _github_enabled() -> bool:
    cfg = _github_config()
    return bool(cfg.get("enabled") == "true" and cfg.get("token") and cfg.get("repo") and cfg.get("branch"))


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "financeportal-target-storage",
    }


def _contents_url(repo: str, path: str) -> str:
    clean_path = path.strip().lstrip("/")
    quoted_path = urllib.parse.quote(clean_path, safe="/")
    return f"https://api.github.com/repos/{repo}/contents/{quoted_path}"


def _github_request(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, data=data, headers=_headers(token), method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        text = response.read().decode("utf-8")
        return json.loads(text) if text else {}


def _read_github(path_override: str | None = None) -> tuple[dict[str, Any], str]:
    cfg = _github_config(path_override=path_override)
    url = _contents_url(cfg["repo"], cfg["path"]) + "?ref=" + cfg["branch"]
    response = _github_request("GET", url, cfg["token"])
    content = str(response.get("content") or "").replace("\n", "")
    sha = str(response.get("sha") or "")
    if not content or not sha:
        raise RuntimeError("Risposta GitHub non valida per target_analisti.json.")
    payload = json.loads(base64.b64decode(content).decode("utf-8"))
    return normalize_payload(payload), sha


def _write_github(payload: dict[str, Any], message: str, path_override: str | None = None) -> None:
    cfg = _github_config(path_override=path_override)
    sha = ""
    try:
        _, sha = _read_github(path_override=cfg["path"])
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    payload = normalize_payload(payload)
    payload["updated_at"] = utc_now_iso()
    encoded = base64.b64encode(json.dumps(payload, indent=4, ensure_ascii=False).encode("utf-8")).decode("utf-8")
    body = {"message": message, "content": encoded, "branch": cfg["branch"]}
    if sha:
        body["sha"] = sha
    _github_request("PUT", _contents_url(cfg["repo"], cfg["path"]), cfg["token"], body)


def set_target_storage_state(mode: str, error: str = "") -> None:
    st.session_state["target_storage_mode"] = mode
    st.session_state["target_last_github_error"] = error
    try:
        cfg = _github_config()
        st.session_state["target_storage_path"] = f"{cfg.get('branch', DEFAULT_TARGET_BRANCH)}/{cfg.get('path', '')}"
    except Exception:
        try:
            st.session_state["target_storage_path"] = str(get_user_targets_path())
        except Exception:
            st.session_state["target_storage_path"] = DEFAULT_TARGET_JSON_PATH


def _initial_payload_for_user(json_path: Path) -> dict[str, Any]:
    """Return first GitHub payload for current user.

    Andrea receives a copy of the legacy global target file when available.
    New users keep the empty local file created by the workspace initializer.
    """
    if get_current_user() == "andrea":
        try:
            payload, _sha = _read_github(path_override=DEFAULT_TARGET_JSON_PATH)
            return normalize_payload(payload)
        except Exception:
            pass
    return _read_local(json_path)


def load_targets(json_path: Path) -> dict[str, Any]:
    ensure_target_file(json_path)

    if _github_enabled():
        try:
            payload, _ = _read_github()
            _write_local(json_path, payload)
            set_target_storage_state("github")
            return payload
        except urllib.error.HTTPError as error:
            if error.code != 404:
                set_target_storage_state("locale_fallback", str(error))
                return _read_local(json_path)
            try:
                payload = _initial_payload_for_user(json_path)
                _write_local(json_path, payload)
                _write_github(payload, "multiuser: crea target analisti utente " + (get_current_user() or "unknown"))
                set_target_storage_state("github")
                return payload
            except Exception as create_exc:
                set_target_storage_state("locale_fallback", str(create_exc))
                return _read_local(json_path)
        except Exception as exc:
            set_target_storage_state("locale_fallback", str(exc))
            return _read_local(json_path)

    set_target_storage_state("locale")
    return _read_local(json_path)


def save_targets(json_path: Path, payload: dict[str, Any]) -> None:
    payload = normalize_payload(payload)
    _write_local(json_path, payload)
    if _github_enabled():
        try:
            _write_github(payload, "Aggiorna target analisti utente " + (get_current_user() or "unknown"))
            set_target_storage_state("github")
        except Exception as exc:
            set_target_storage_state("locale_fallback", str(exc))
    else:
        set_target_storage_state("locale")


def get_saved_target(json_path: Path, yf_symbol: str) -> dict | None:
    payload = load_targets(json_path)
    item = payload.get("targets", {}).get(_key(yf_symbol))
    return item if isinstance(item, dict) else None


def upsert_target(json_path: Path, yf_symbol: str, data: dict) -> dict:
    payload = load_targets(json_path)
    targets = payload.setdefault("targets", {})
    clean_key = _key(yf_symbol)
    item = dict(data or {})
    item["yf_symbol"] = clean_key
    item["updated_at"] = item.get("updated_at") or utc_now_iso()
    targets[clean_key] = item
    save_targets(json_path, payload)
    return item
