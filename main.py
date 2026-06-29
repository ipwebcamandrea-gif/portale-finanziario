import streamlit as st
from pathlib import Path

from utils.app_branding import get_app_icon, render_app_icon_meta
from utils.auth import (
    is_authenticated,
    login_user,
    logout_user,
)
from utils.user_context import normalize_user_id


# =========================
# CONFIGURAZIONE PAGINA
# =========================

st.set_page_config(
    page_title="FinancePortal 2026",
    page_icon=get_app_icon(),
    layout="centered"
)
render_app_icon_meta()


# =========================
# CONFIGURAZIONE FILE / CSS
# =========================

ROOT_DIR = Path(__file__).resolve().parent

GLOBAL_CSS = ROOT_DIR / "css" / "global.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(
                f"<style>{file.read()}</style>",
                unsafe_allow_html=True
            )


local_css(GLOBAL_CSS)


# =========================
# CSS INLINE LOGIN SPECIFICO
# =========================

st.markdown(
    """
    <style>
    div[data-testid="stForm"] {
        max-width: 440px;
        margin: 0 auto;
    }
    .login-subtitle {
        max-width: 440px;
        margin: 0 auto 1rem auto;
        color: var(--text-main);
        font-size: 1.45rem;
        font-weight: 850;
        line-height: 1.2;
        text-align: left;
    }
    @media screen and (max-width: 768px) {
        .login-subtitle {
            max-width: 100%;
            font-size: 1.25rem;
            margin-bottom: 0.85rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================
# SESSION STATE
# =========================

if "authenticated" not in st.session_state:
    # Do not call logout_user() here: after browser F5 the restore token in
    # query params must remain available so is_authenticated() can rebuild
    # session_state without sending the user back to login.
    st.session_state["authenticated"] = False


# =========================
# CREDENZIALI MULTIUTENTE
# =========================

def _as_plain_dict(value):
    """Convert Streamlit secrets/AttrDict objects to regular dictionaries."""
    if hasattr(value, "items"):
        return {key: _as_plain_dict(item) for key, item in value.items()}
    return value


def _is_enabled(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off", "disabled"}


def load_users_from_secrets() -> dict:
    """Load enabled users from Streamlit Secrets.

    Supported simple format:

    [credentials.usernames]
    andrea = "PASSWORD"
    test = "PASSWORD"

    Supported extended format:

    [credentials.usernames.andrea]
    password = "PASSWORD"
    display_name = "Andrea"
    enabled = true
    """
    try:
        raw_usernames = st.secrets["credentials"]["usernames"]
    except Exception:
        return {}

    raw_usernames = _as_plain_dict(raw_usernames)
    if not hasattr(raw_usernames, "items"):
        return {}

    users = {}
    for raw_username, raw_config in raw_usernames.items():
        user_id = normalize_user_id(raw_username)
        if not user_id:
            continue

        if hasattr(raw_config, "items"):
            config = _as_plain_dict(raw_config)
            password = str(config.get("password") or config.get("pwd") or config.get("pass") or "")
            display_name = str(config.get("display_name") or config.get("name") or raw_username).strip()
            enabled = _is_enabled(config.get("enabled", True))
        else:
            password = str(raw_config or "")
            display_name = str(raw_username).strip()
            enabled = True

        if not enabled or not password:
            continue

        users[user_id] = {
            "password": password,
            "display_name": display_name or user_id,
        }

    return users


USERS = load_users_from_secrets()


# =========================
# SE GIÀ AUTENTICATO
# =========================

if is_authenticated():
    st.switch_page("pages/dashboard.py")


# =========================
# INTERFACCIA LOGIN
# =========================

st.markdown(
    '<div class="hero-title">FinancePortal 2026</div>',
    unsafe_allow_html=True
)

with st.container(key="login_card"):
    st.markdown('<div class="login-subtitle">Accedi al sistema</div>', unsafe_allow_html=True)

    if not USERS:
        st.error(
            "Nessun utente configurato nei Secrets di Streamlit. "
            "Configura almeno un utente in [credentials.usernames]."
        )
        st.stop()

    with st.form("login_form"):
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Entra nella Dashboard")

    if submitted:
        user_id = normalize_user_id(user)
        credentials = USERS.get(user_id)

        if credentials and password.strip() == str(credentials.get("password", "")):
            login_user(user_id, credentials.get("display_name", user_id))
            st.switch_page("pages/dashboard.py")
        else:
            logout_user()
            st.error("Credenziali non valide")
