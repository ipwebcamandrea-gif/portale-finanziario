from __future__ import annotations

import base64
import json
from functools import lru_cache
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

APP_TITLE = "FinancePortal 2026"
APP_SHORT_NAME = "FinancePortal"
APP_THEME_COLOR = "#0E1117"
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


@lru_cache(maxsize=1)
def _app_icon_data_uri() -> str:
    try:
        if APP_ICON_PATH.exists():
            return "data:image/png;base64," + base64.b64encode(APP_ICON_PATH.read_bytes()).decode("ascii")
    except Exception:
        pass
    return ""


@lru_cache(maxsize=1)
def _manifest_data_uri() -> str:
    icon_uri = _app_icon_data_uri()
    if not icon_uri:
        return ""

    manifest = {
        "name": APP_TITLE,
        "short_name": APP_SHORT_NAME,
        "start_url": ".",
        "scope": ".",
        "display": "standalone",
        "background_color": APP_THEME_COLOR,
        "theme_color": APP_THEME_COLOR,
        "icons": [
            {
                "src": icon_uri,
                "sizes": "192x192 512x512",
                "type": "image/png",
                "purpose": "any maskable",
            }
        ],
    }
    raw = json.dumps(manifest, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "data:application/manifest+json;base64," + base64.b64encode(raw).decode("ascii")


def render_app_icon_meta() -> None:
    """Apply the custom icon to favicon, Apple touch icon and mobile manifest."""
    icon_uri = _app_icon_data_uri()
    if not icon_uri:
        return

    manifest_uri = _manifest_data_uri()

    components.html(
        f"""
<script>
(function() {{
  const doc = window.parent.document;
  const icon = {json.dumps(icon_uri)};
  const manifest = {json.dumps(manifest_uri)};

  function upsertLink(rel, href, type) {{
    doc.querySelectorAll('link[rel="' + rel + '"]').forEach(function(node) {{ node.remove(); }});
    const link = doc.createElement('link');
    link.setAttribute('rel', rel);
    if (type) link.setAttribute('type', type);
    link.setAttribute('href', href);
    doc.head.appendChild(link);
  }}

  upsertLink('icon', icon, 'image/png');
  upsertLink('shortcut icon', icon, 'image/png');
  upsertLink('apple-touch-icon', icon, 'image/png');
  if (manifest) upsertLink('manifest', manifest, 'application/manifest+json');

  let theme = doc.querySelector('meta[name="theme-color"]');
  if (!theme) {{
    theme = doc.createElement('meta');
    theme.setAttribute('name', 'theme-color');
    doc.head.appendChild(theme);
  }}
  theme.setAttribute('content', {json.dumps(APP_THEME_COLOR)});
}})();
</script>
""",
        height=0,
        width=0,
    )
