from __future__ import annotations

from pathlib import Path

APP_TITLE = "FinancePortal 2026"
APP_ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "app_icon.png"


def get_app_icon():
    """Return the custom app icon for Streamlit page_config, with safe fallback."""
    try:
        from PIL import Image
        if APP_ICON_PATH.exists():
            return Image.open(APP_ICON_PATH)
    except Exception:
        pass
    return "📈"
