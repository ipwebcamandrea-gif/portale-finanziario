from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import streamlit as st

from utils.user_context import clear_current_user, get_current_user, set_current_user


# =========================
# SESSION CONFIG
# =========================
# Timeout applicativo: 30 minuti di inattività.
# Nota: questo è diverso da server.disconnectedSessionTTL di Streamlit,
# che riguarda la sessione disconnessa lato server.
SESSION_TIMEOUT_SECONDS = 30 * 60

_AUTHENTICATED_KEY = "authenticated"
_AUTH_LOGIN_TS_KEY = "auth_login_ts"
_AUTH_LAST_ACTIVITY_TS_KEY = "auth_last_activity_ts"
_AUTH_EXPIRES_AT_TS_KEY = "auth_expires_at_ts"
_AUTH_EXPIRED_FLAG_KEY = "auth_session_expired"
_AUTH_RESTORE_QUERY_PARAM = "fp_auth"
_AUTH_TOKEN_VERSION = 1



# Session keys that can leak page selections/data between users if not cleared.
_VOLATILE_SESSION_PREFIXES = (
    "target_",
    "ticker_",
    "tv_",
    "portfolio_",
    "allocation_",
)

_VOLATILE_SESSION_KEYS = {
    "ticker_selezionato",
    "lista_tickers",
    "target_selected",
    "target_source",
    "target_yf_symbol",
    "target_ticker",
    "target_tv_symbol",
    "target_name",
    "target_market",
    "target_currency",
}


def _now_ts() -> float:
    return time.time()

def _auth_secret_key() -> bytes:
    """Return a stable HMAC key for refresh recovery tokens.

    Recommended optional secret:

    [auth]
    token_secret = "LONG_RANDOM_STRING"

    Fallback uses the loaded Streamlit secrets representation so no extra setup is
    required for the current deployment.
    """
    candidates = []
    try:
        candidates.append(str(st.secrets.get("auth_token_secret", "") or ""))
    except Exception:
        pass
    try:
        auth_section = st.secrets.get("auth", {})
        if hasattr(auth_section, "get"):
            candidates.append(str(auth_section.get("token_secret", "") or ""))
    except Exception:
        pass
    try:
        candidates.append(str(st.secrets))
    except Exception:
        pass

    secret = next((item for item in candidates if item.strip()), "financeportal-local-dev-key")
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _sign_payload(payload_part: str) -> str:
    digest = hmac.new(_auth_secret_key(), payload_part.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def _create_restore_token(user_id: str, display_name: str = "", now: float | None = None) -> str:
    now = _now_ts() if now is None else now
    payload = {
        "v": _AUTH_TOKEN_VERSION,
        "u": str(user_id or ""),
        "d": str(display_name or user_id or ""),
        "iat": int(now),
        "exp": int(now + SESSION_TIMEOUT_SECONDS),
    }
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature_part = _sign_payload(payload_part)
    return payload_part + "." + signature_part


def _decode_restore_token(token: str) -> dict | None:
    token = str(token or "").strip()
    if not token or "." not in token:
        return None

    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = _sign_payload(payload_part)
    if not hmac.compare_digest(signature_part, expected_signature):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except Exception:
        return None

    if int(payload.get("v", 0) or 0) != _AUTH_TOKEN_VERSION:
        return None

    try:
        expires_at = float(payload.get("exp", 0) or 0)
    except Exception:
        return None

    if expires_at <= _now_ts():
        return None

    user_id = str(payload.get("u", "") or "").strip()
    if not user_id:
        return None

    return payload


def _get_restore_query_token() -> str:
    try:
        value = st.query_params.get(_AUTH_RESTORE_QUERY_PARAM, "")
        if isinstance(value, list):
            return str(value[0] if value else "")
        return str(value or "")
    except Exception:
        return ""


def _set_restore_query_token(token: str) -> None:
    try:
        st.query_params[_AUTH_RESTORE_QUERY_PARAM] = token
    except Exception:
        pass


def _clear_restore_query_token() -> None:
    try:
        if _AUTH_RESTORE_QUERY_PARAM in st.query_params:
            del st.query_params[_AUTH_RESTORE_QUERY_PARAM]
    except Exception:
        pass


def _refresh_restore_token(now: float | None = None) -> None:
    """Write a signed short-lived restore token into the URL query params."""
    user_id = get_current_user()
    if not user_id or not bool(st.session_state.get(_AUTHENTICATED_KEY, False)):
        return
    display_name = str(st.session_state.get("current_user_display_name", user_id) or user_id)
    token = _create_restore_token(user_id, display_name, now)
    _set_restore_query_token(token)


def _restore_auth_from_query_token() -> bool:
    """Restore Streamlit session_state after browser hard refresh/F5.

    The token is signed and short-lived. It does not contain the password.
    """
    if bool(st.session_state.get(_AUTHENTICATED_KEY, False)):
        return True

    payload = _decode_restore_token(_get_restore_query_token())
    if not payload:
        return False

    now = _now_ts()
    user_id = str(payload.get("u", "") or "").strip()
    display_name = str(payload.get("d", "") or user_id).strip()
    set_current_user(user_id, display_name)
    st.session_state[_AUTHENTICATED_KEY] = True
    st.session_state[_AUTH_LOGIN_TS_KEY] = float(payload.get("iat", now) or now)
    st.session_state[_AUTH_LAST_ACTIVITY_TS_KEY] = now
    st.session_state[_AUTH_EXPIRES_AT_TS_KEY] = now + SESSION_TIMEOUT_SECONDS
    st.session_state.pop(_AUTH_EXPIRED_FLAG_KEY, None)
    _refresh_restore_token(now)
    return True



def _clear_auth_timestamps() -> None:
    for key in (
        _AUTH_LOGIN_TS_KEY,
        _AUTH_LAST_ACTIVITY_TS_KEY,
        _AUTH_EXPIRES_AT_TS_KEY,
    ):
        st.session_state.pop(key, None)


def _clear_volatile_session_state() -> None:
    """Clear page-specific state so users cannot inherit another user's UI state."""
    keys_to_delete = []
    for key in list(st.session_state.keys()):
        if key in _VOLATILE_SESSION_KEYS:
            keys_to_delete.append(key)
            continue
        if any(str(key).startswith(prefix) for prefix in _VOLATILE_SESSION_PREFIXES):
            keys_to_delete.append(key)

    for key in keys_to_delete:
        st.session_state.pop(key, None)


def _touch_session(now: float | None = None) -> None:
    """Refresh last activity, computed expiry timestamp and refresh-recovery token."""
    now = _now_ts() if now is None else now
    st.session_state[_AUTH_LAST_ACTIVITY_TS_KEY] = now
    st.session_state[_AUTH_EXPIRES_AT_TS_KEY] = now + SESSION_TIMEOUT_SECONDS
    _refresh_restore_token(now)


def _is_session_expired(now: float | None = None) -> bool:
    """Return True if the authenticated session exceeded inactivity timeout."""
    if not bool(st.session_state.get(_AUTHENTICATED_KEY, False)):
        return False

    now = _now_ts() if now is None else now
    last_activity = st.session_state.get(_AUTH_LAST_ACTIVITY_TS_KEY)

    # Compatibility with sessions created before this timeout logic existed:
    # if the user is already authenticated but has no timestamp, initialize it
    # instead of forcing an immediate logout after deployment.
    if last_activity is None:
        st.session_state.setdefault(_AUTH_LOGIN_TS_KEY, now)
        _touch_session(now)
        return False

    try:
        elapsed = now - float(last_activity)
    except Exception:
        return True

    return elapsed > SESSION_TIMEOUT_SECONDS


def get_session_timeout_seconds() -> int:
    """Expose configured inactivity timeout for diagnostics/UI if needed."""
    return SESSION_TIMEOUT_SECONDS


def get_session_remaining_seconds() -> int:
    """Return remaining seconds before inactivity timeout, or 0 if expired."""
    if not bool(st.session_state.get(_AUTHENTICATED_KEY, False)):
        return 0

    expires_at = st.session_state.get(_AUTH_EXPIRES_AT_TS_KEY)
    if expires_at is None:
        return SESSION_TIMEOUT_SECONDS

    try:
        return max(0, int(float(expires_at) - _now_ts()))
    except Exception:
        return 0


# =========================
# CHECK AUTH
# =========================

def is_authenticated() -> bool:
    """Return True only if user is logged in, has a current user and timeout is valid."""
    if not bool(st.session_state.get(_AUTHENTICATED_KEY, False)):
        if not _restore_auth_from_query_token():
            return False

    if not get_current_user():
        logout_user()
        return False

    if _is_session_expired():
        logout_user(session_expired=True)
        return False

    return True


# =========================
# PROTEZIONE PAGINE
# =========================

def require_login() -> None:
    """Protect a page and refresh last activity on every valid page access."""
    if not is_authenticated():
        if st.session_state.get(_AUTH_EXPIRED_FLAG_KEY, False):
            st.warning("Sessione scaduta per inattività. Effettua di nuovo il login.")
        else:
            st.error("Accesso non autorizzato.")

        if st.button("Torna al Login"):
            st.switch_page("main.py")

        st.stop()

    _touch_session()


# =========================
# LOGIN / LOGOUT
# =========================

def login_user(user_id: str, display_name: str = "") -> None:
    """Mark user as authenticated and start inactivity timer."""
    now = _now_ts()
    set_current_user(user_id, display_name)
    st.session_state[_AUTHENTICATED_KEY] = True
    st.session_state[_AUTH_LOGIN_TS_KEY] = now
    st.session_state[_AUTH_LAST_ACTIVITY_TS_KEY] = now
    st.session_state[_AUTH_EXPIRES_AT_TS_KEY] = now + SESSION_TIMEOUT_SECONDS
    st.session_state.pop(_AUTH_EXPIRED_FLAG_KEY, None)
    _refresh_restore_token(now)


def logout_user(session_expired: bool = False) -> None:
    """Logout user and clear auth-related/volatile session state."""
    st.session_state[_AUTHENTICATED_KEY] = False
    clear_current_user()
    _clear_auth_timestamps()
    _clear_volatile_session_state()
    _clear_restore_query_token()

    if session_expired:
        st.session_state[_AUTH_EXPIRED_FLAG_KEY] = True
    else:
        st.session_state.pop(_AUTH_EXPIRED_FLAG_KEY, None)


def logout_and_redirect() -> None:
    logout_user()
    st.switch_page("main.py")
