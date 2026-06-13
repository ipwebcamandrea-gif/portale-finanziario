from __future__ import annotations

from collections.abc import Callable

import streamlit as st


def render_topbar(
    *,
    show_refresh: bool = True,
    show_mobile_toggle: bool = True,
    mobile_key: str = "mobile_view",
    mobile_default: bool = True,
    back_target: str = "pages/dashboard.py",
    refresh_callback: Callable[[], None] | None = None,
    refresh_help: str = "Aggiorna",
) -> bool:
    """Render a standard topbar shared by app pages.

    The function returns the mobile-view state. If `show_mobile_toggle` is
    False, the returned value still follows the session default for consistency.
    """

    if mobile_key not in st.session_state:
        st.session_state[mobile_key] = mobile_default

    st.markdown('<div class="fp-topbar-anchor"></div>', unsafe_allow_html=True)

    col_back, col_refresh, col_mobile, _ = st.columns([1.35, 0.62, 1.45, 6.58])

    with col_back:
        if st.button("← Cockpit", key=f"{mobile_key}_back", use_container_width=True):
            try:
                st.switch_page(back_target)
            except Exception:
                st.switch_page("main.py")

    with col_refresh:
        if show_refresh:
            if st.button("🔄", key=f"{mobile_key}_refresh", help=refresh_help, use_container_width=True):
                if refresh_callback is not None:
                    refresh_callback()
                else:
                    st.rerun()

    mobile_view = bool(st.session_state.get(mobile_key, mobile_default))

    with col_mobile:
        if show_mobile_toggle:
            mobile_view = st.toggle("Vista mobile", value=mobile_view, key=mobile_key)

    return bool(mobile_view)
