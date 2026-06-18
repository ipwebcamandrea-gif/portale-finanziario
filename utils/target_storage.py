from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from utils.portfolio_storage import get_portfolio_github_config


DEFAULT_TARGET_BRANCH = "data-watchlists"
DEFAULT_TARGET_JSON_PATH = "portfolio/target_analisti.json"


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


def _github_config() -> dict[str, str]:
    cfg = get_portfolio_github_config()
    return {
        "token": cfg.get("token", ""),
        "repo": cfg.get("repo", ""),
        "branch": cfg.get("branch") or DEFAULT_TARGET_BRANCH,
        "path": DEFAULT_TARGET_JSON_PATH,
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
    return f"https://api.github.com/repos/{repo}/contents/{path.lstrip('/')}"


def _github_request(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, data=data, headers=_headers(token), method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        text = response.read().decode("utf-8")
        return json.loads(text) if text else {}


def _read_github() -> tuple[dict[str, Any], str]:
    cfg = _github_config()
    url = _contents_url(cfg["repo"], cfg["path"]) + "?ref=" + cfg["branch"]
    response = _github_request("GET", url, cfg["token"])
    content = str(response.get("content") or "").replace("\n", "")
    sha = str(response.get("sha") or "")
    if not content or not sha:
        raise RuntimeError("Risposta GitHub non valida per target_analisti.json.")
    payload = json.loads(base64.b64decode(content).decode("utf-8"))
    return normalize_payload(payload), sha


def _write_github(payload: dict[str, Any], message: str) -> None:
    cfg = _github_config()
    sha = ""
    try:
        _, sha = _read_github()
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


def load_targets(json_path: Path) -> dict[str, Any]:
    if _github_enabled():
        try:
            payload, _ = _read_github()
            _write_local(json_path, payload)
            set_target_storage_state("github")
            return payload
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
            _write_github(payload, "Aggiorna target analisti")
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
