from __future__ import annotations

from pathlib import Path

from utils.user_context import get_current_user, normalize_user_id


ROOT_DIR = Path(__file__).resolve().parent.parent
USER_DATA_ROOT = ROOT_DIR / "data" / "users"

# GitHub persistence uses branch "data-watchlists"; paths below are branch-relative.
GITHUB_DATA_BRANCH = "data-watchlists"
GITHUB_USERS_ROOT = "users"


# =========================
# LOCAL USER PATHS
# =========================

def get_user_id(user_id: str | None = None) -> str:
    """Return a normalized user id, using the current session user by default."""
    normalized = normalize_user_id(user_id or get_current_user())
    if not normalized:
        raise RuntimeError("Utente corrente non disponibile: impossibile risolvere i path dati.")
    return normalized


def get_user_data_dir(user_id: str | None = None) -> Path:
    """Return local data directory for a user."""
    return USER_DATA_ROOT / get_user_id(user_id)


def get_user_watchlists_path(user_id: str | None = None) -> Path:
    """Return local Watchlist JSON path for a user."""
    return get_user_data_dir(user_id) / "watchlists.json"


def get_user_portfolio_path(user_id: str | None = None) -> Path:
    """Return local Portafoglio JSON path for a user."""
    return get_user_data_dir(user_id) / "portafoglio.json"


def get_user_targets_path(user_id: str | None = None) -> Path:
    """Return local Target Analisti JSON path for a user."""
    return get_user_data_dir(user_id) / "target_analisti.json"


def ensure_user_data_dir(user_id: str | None = None) -> Path:
    """Create and return the local data directory for a user."""
    data_dir = get_user_data_dir(user_id)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# =========================
# GITHUB USER PATHS
# =========================

def get_user_github_watchlists_path(user_id: str | None = None) -> str:
    """Return branch-relative GitHub Watchlist path for a user.

    The full logical location is:
    data-watchlists/users/<utente>/watchlists.json
    """
    return f"{GITHUB_USERS_ROOT}/{get_user_id(user_id)}/watchlists.json"


def get_user_github_watchlists_display_path(user_id: str | None = None) -> str:
    """Return human-readable GitHub Watchlist path including branch name."""
    return f"{GITHUB_DATA_BRANCH}/{get_user_github_watchlists_path(user_id)}"


def get_user_github_portfolio_path(user_id: str | None = None) -> str:
    """Return branch-relative GitHub Portafoglio path for a user."""
    return f"{GITHUB_USERS_ROOT}/{get_user_id(user_id)}/portafoglio.json"


def get_user_github_targets_path(user_id: str | None = None) -> str:
    """Return branch-relative GitHub Target Analisti path for a user."""
    return f"{GITHUB_USERS_ROOT}/{get_user_id(user_id)}/target_analisti.json"


# =========================
# LEGACY GLOBAL PATHS
# =========================

def get_legacy_watchlists_path() -> Path:
    return ROOT_DIR / "watchlists.json"


def get_legacy_portfolio_path() -> Path:
    return ROOT_DIR / "portfolio" / "portafoglio.json"


def get_legacy_targets_path() -> Path:
    return ROOT_DIR / "portfolio" / "target_analisti.json"
