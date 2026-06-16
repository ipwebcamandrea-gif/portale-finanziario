from __future__ import annotations

import time

import streamlit as st


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


def _now_ts() -> float:
    return time.time()


def _clear_auth_timestamps() -> None:
    for key in (
        _AUTH_LOGIN_TS_KEY,
        _AUTH_LAST_ACTIVITY_TS_KEY,
        _AUTH_EXPIRES_AT_TS_KEY,
    ):
        st.session_state.pop(key, None)


def _touch_session(now: float | None = None) -> None:
    """Refresh last activity and computed expiry timestamp."""
    now = _now_ts() if now is None else now
    st.session_state[_AUTH_LAST_ACTIVITY_TS_KEY] = now
    st.session_state[_AUTH_EXPIRES_AT_TS_KEY] = now + SESSION_TIMEOUT_SECONDS


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
    """Return True only if user is logged in and inactivity timeout is valid."""
    if not bool(st.session_state.get(_AUTHENTICATED_KEY, False)):
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

def login_user() -> None:
    """Mark user as authenticated and start inactivity timer."""
    now = _now_ts()
    st.session_state[_AUTHENTICATED_KEY] = True
    st.session_state[_AUTH_LOGIN_TS_KEY] = now
    st.session_state[_AUTH_LAST_ACTIVITY_TS_KEY] = now
    st.session_state[_AUTH_EXPIRES_AT_TS_KEY] = now + SESSION_TIMEOUT_SECONDS
    st.session_state.pop(_AUTH_EXPIRED_FLAG_KEY, None)


def logout_user(session_expired: bool = False) -> None:
    """Logout user and clear auth-related/volatile session state."""
    st.session_state[_AUTHENTICATED_KEY] = False
    _clear_auth_timestamps()

    if session_expired:
        st.session_state[_AUTH_EXPIRED_FLAG_KEY] = True
    else:
        st.session_state.pop(_AUTH_EXPIRED_FLAG_KEY, None)

    chiavi_da_rimuovere = [
        "ticker_selezionato",
        "lista_tickers",
    ]

    for chiave in chiavi_da_rimuovere:
        if chiave in st.session_state:
            del st.session_state[chiave]


def logout_and_redirect() -> None:
    logout_user()
    st.switch_page("main.py")
