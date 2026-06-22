from __future__ import annotations

import re

import streamlit as st

CURRENT_USER_KEY = "current_user"
CURRENT_USER_DISPLAY_NAME_KEY = "current_user_display_name"


def normalize_user_id(value: str) -> str:
    """Return a filesystem/session safe lowercase user id.

    Examples:
    Andrea -> andrea
    andrea.rosso -> andrea_rosso
    """
    cleaned = str(value or "").strip().lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "_", cleaned)
    cleaned = cleaned.strip("_")
    return cleaned


def get_current_user(default: str = "") -> str:
    """Return current authenticated user id from session_state."""
    return normalize_user_id(st.session_state.get(CURRENT_USER_KEY, default))


def get_current_user_display_name(default: str = "") -> str:
    """Return display name for the current authenticated user."""
    value = str(st.session_state.get(CURRENT_USER_DISPLAY_NAME_KEY, "") or "").strip()
    if value:
        return value
    user_id = get_current_user()
    return user_id or default


def set_current_user(user_id: str, display_name: str = "") -> None:
    """Store current user identity in session_state."""
    normalized = normalize_user_id(user_id)
    st.session_state[CURRENT_USER_KEY] = normalized
    st.session_state[CURRENT_USER_DISPLAY_NAME_KEY] = str(display_name or normalized).strip() or normalized


def clear_current_user() -> None:
    """Remove current user identity from session_state."""
    st.session_state.pop(CURRENT_USER_KEY, None)
    st.session_state.pop(CURRENT_USER_DISPLAY_NAME_KEY, None)
