from __future__ import annotations

import json

import streamlit.components.v1 as components


# =========================
# AUTO REFRESH PAGE HELPER
# =========================

def render_auto_refresh_timer(*, key: str, interval_seconds: int = 120, enabled: bool = True) -> None:
    """Render a browser-side timer that reloads the current Streamlit page.

    Streamlit reruns Python code only after a user interaction or a browser
    reload. This helper creates the missing browser-side timer. The timer is
    intentionally isolated in this utility module so the rest of the project
    stays free from scattered JavaScript.

    If enabled is False, any existing timer for the same key is cancelled. This
    is useful while edit/delete/simulation panels are open.
    """
    safe_key = str(key or "auto_refresh")
    interval_ms = max(int(interval_seconds), 10) * 1000
    enabled_js = "true" if enabled else "false"
    key_js = json.dumps(safe_key)

    components.html(
        f"""
        <script>
        (function() {{
            const timerKey = {key_js};
            const intervalMs = {interval_ms};
            const enabled = {enabled_js};
            const parentWindow = window.parent || window;

            parentWindow.__financePortalAutoRefreshTimers = parentWindow.__financePortalAutoRefreshTimers || {{}};

            if (parentWindow.__financePortalAutoRefreshTimers[timerKey]) {{
                clearTimeout(parentWindow.__financePortalAutoRefreshTimers[timerKey]);
                delete parentWindow.__financePortalAutoRefreshTimers[timerKey];
            }}

            if (!enabled) {{
                return;
            }}

            parentWindow.__financePortalAutoRefreshTimers[timerKey] = setTimeout(function() {{
                parentWindow.location.reload();
            }}, intervalMs);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )
