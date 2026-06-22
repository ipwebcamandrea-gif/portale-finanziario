from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from utils.user_context import get_current_user
from utils.user_paths import (
    ensure_user_data_dir,
    get_legacy_portfolio_path,
    get_legacy_targets_path,
    get_legacy_watchlists_path,
    get_user_portfolio_path,
    get_user_targets_path,
    get_user_watchlists_path,
)


MIGRATION_SOURCE_USER = "andrea"
_MIGRATION_DONE_SESSION_PREFIX = "multiuser_workspace_ready_"


# =========================
# DEFAULT EMPTY DATA
# =========================

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_watchlists_payload() -> dict:
    """Return empty Watchlist payload for new users."""
    return {
        "version": 1,
        "active_watchlist": "Default",
        "watchlists": {
            "Default": [],
        },
    }


def empty_portfolio_payload() -> dict:
    """Return empty Portafoglio payload for new users."""
    return {
        "version": 1,
        "updated_at": _utc_now_iso(),
        "positions": [],
    }


def empty_targets_payload() -> dict:
    """Return empty Target Analisti payload for new users."""
    return {
        "version": 1,
        "updated_at": _utc_now_iso(),
        "targets": {},
    }


def _write_json_if_missing(path: Path, payload: dict) -> bool:
    """Write JSON only when path does not already exist. Return True if created."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def _copy_if_source_exists_and_target_missing(source: Path, target: Path) -> bool:
    """Copy source to target only if source exists and target is missing."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or not source.exists():
        return False
    shutil.copy2(source, target)
    return True


# =========================
# USER WORKSPACE SETUP
# =========================

def ensure_user_workspace(user_id: str) -> dict:
    """Create local user workspace and initial JSON files.

    Andrea receives a copy of the current legacy data when available.
    All other users receive empty JSON files.

    This function is intentionally non-destructive: it never overwrites existing
    user files and never moves/deletes legacy files.
    """
    user_id = str(user_id or "").strip().lower()
    if not user_id:
        raise RuntimeError("Utente non disponibile: impossibile preparare workspace multiutente.")

    ensure_user_data_dir(user_id)

    user_watchlists_path = get_user_watchlists_path(user_id)
    user_portfolio_path = get_user_portfolio_path(user_id)
    user_targets_path = get_user_targets_path(user_id)

    result = {
        "user_id": user_id,
        "copied": [],
        "created_empty": [],
        "existing": [],
    }

    if user_id == MIGRATION_SOURCE_USER:
        copy_plan = [
            (get_legacy_watchlists_path(), user_watchlists_path, "watchlists"),
            (get_legacy_portfolio_path(), user_portfolio_path, "portfolio"),
            (get_legacy_targets_path(), user_targets_path, "targets"),
        ]
        for source, target, label in copy_plan:
            if _copy_if_source_exists_and_target_missing(source, target):
                result["copied"].append(label)

    empty_plan = [
        (user_watchlists_path, empty_watchlists_payload(), "watchlists"),
        (user_portfolio_path, empty_portfolio_payload(), "portfolio"),
        (user_targets_path, empty_targets_payload(), "targets"),
    ]
    for path, payload, label in empty_plan:
        if _write_json_if_missing(path, payload):
            result["created_empty"].append(label)
        else:
            result["existing"].append(label)

    return result


def ensure_current_user_workspace() -> dict | None:
    """Create current user's workspace once per Streamlit session."""
    user_id = get_current_user()
    if not user_id:
        return None

    session_key = _MIGRATION_DONE_SESSION_PREFIX + user_id
    if st.session_state.get(session_key):
        return st.session_state.get(session_key + "_result")

    result = ensure_user_workspace(user_id)
    st.session_state[session_key] = True
    st.session_state[session_key + "_result"] = result
    return result
