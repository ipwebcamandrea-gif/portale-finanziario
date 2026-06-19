from __future__ import annotations

import base64
import json
from pathlib import Path

APP_TITLE = "FinancePortal 2026"
APP_SHORT_TITLE = "FinancePortal"
APP_THEME_COLOR = "#0e1117"
APP_BACKGROUND_COLOR = "#0e1117"
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


def _icon_data_uri() -> str:
    """Return the existing app icon as a data URI without exposing a static route."""
    try:
        if APP_ICON_PATH.exists():
            encoded = base64.b64encode(APP_ICON_PATH.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
    except Exception:
        pass
    return ""


def _manifest_data_uri(icon_uri: str) -> str:
    """Build an in-memory web manifest that references the existing app icon."""
    manifest = {
        "name": APP_TITLE,
        "short_name": APP_SHORT_TITLE,
        "description": "FinancePortal 2026",
        "start_url": ".",
        "scope": ".",
        "display": "standalone",
        "orientation": "portrait",
        "theme_color": APP_THEME_COLOR,
        "background_color": APP_BACKGROUND_COLOR,
        "icons": [],
    }
    if icon_uri:
        manifest["icons"] = [
            {"src": icon_uri, "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": icon_uri, "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ]
    encoded = base64.b64encode(json.dumps(manifest, separators=(",", ":")).encode("utf-8")).decode("ascii")
    return f"data:application/manifest+json;base64,{encoded}"


def apply_mobile_app_branding() -> None:
    """Inject mobile/PWA metadata for Android/iOS home-screen shortcuts.

    Streamlit's page_icon updates the browser favicon, but mobile home-screen
    shortcuts often rely on apple-touch-icon and web manifest metadata.
    This function uses the existing assets/app_icon.png without overwriting it.
    """
    icon_uri = _icon_data_uri()
    manifest_uri = _manifest_data_uri(icon_uri)

    try:
        import streamlit.components.v1 as components
    except Exception:
        return

    payload = {
        "appTitle": APP_TITLE,
        "shortTitle": APP_SHORT_TITLE,
        "themeColor": APP_THEME_COLOR,
        "backgroundColor": APP_BACKGROUND_COLOR,
        "iconUri": icon_uri,
        "manifestUri": manifest_uri,
    }
    payload_json = json.dumps(payload)

    components.html(
        f"""
        <script>
        (function() {{
          const cfg = {payload_json};
          const doc = window.parent.document;

          function upsertMeta(name, content) {{
            let el = doc.querySelector('meta[name="' + name + '"]');
            if (!el) {{
              el = doc.createElement('meta');
              el.setAttribute('name', name);
              doc.head.appendChild(el);
            }}
            el.setAttribute('content', content);
          }}

          function upsertLink(id, rel, href, sizes, type) {{
            if (!href) return;
            let el = doc.getElementById(id);
            if (!el) {{
              el = doc.createElement('link');
              el.setAttribute('id', id);
              doc.head.appendChild(el);
            }}
            el.setAttribute('rel', rel);
            el.setAttribute('href', href);
            if (sizes) el.setAttribute('sizes', sizes);
            if (type) el.setAttribute('type', type);
          }}

          upsertMeta('application-name', cfg.shortTitle);
          upsertMeta('apple-mobile-web-app-title', cfg.shortTitle);
          upsertMeta('apple-mobile-web-app-capable', 'yes');
          upsertMeta('mobile-web-app-capable', 'yes');
          upsertMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');
          upsertMeta('theme-color', cfg.themeColor);
          upsertMeta('msapplication-TileColor', cfg.backgroundColor);

          upsertLink('fp-app-icon', 'icon', cfg.iconUri, '512x512', 'image/png');
          upsertLink('fp-apple-touch-icon', 'apple-touch-icon', cfg.iconUri, '180x180', 'image/png');
          upsertLink('fp-manifest', 'manifest', cfg.manifestUri, '', 'application/manifest+json');
        }})();
        </script>
        """,
        height=0,
        width=0,
    )
