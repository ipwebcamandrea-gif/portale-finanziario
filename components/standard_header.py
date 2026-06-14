from __future__ import annotations

from collections.abc import Callable

import streamlit as st


def _go_to_cockpit(back_target: str) -> None:
    try:
        st.switch_page(back_target)
    except Exception:
        st.switch_page("main.py")


def render_standard_page_header(
    *,
    title: str,
    subtitle: str,
    toggle_label: str,
    toggle_key: str,
    toggle_default: bool = True,
    refresh_key: str,
    back_key: str,
    refresh_callback: Callable[[], None] | None = None,
    back_target: str = "pages/dashboard.py",
) -> bool:
    """Render the unified application header.

    Desktop layout follows the Watchlist TradingView pattern:
    [title + subtitle] [toggle] [refresh] [back].

    On smartphone Streamlit can stack columns; the controls remain in the same
    order and inside the available width.
    """

    if toggle_key not in st.session_state:
        st.session_state[toggle_key] = toggle_default

    left_col, right_col = st.columns([3.55, 2.45], vertical_alignment="center")

    with left_col:
        st.markdown(
            f"""
            <div class="std-page-header">
                <div class="std-page-title">{title}</div>
                <div class="std-page-subtitle">{subtitle}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        compact_col, refresh_col, back_col = st.columns(
            [1.55, 0.42, 1.10],
            vertical_alignment="center",
            gap="small",
        )

        with compact_col:
            current_value = bool(st.session_state.get(toggle_key, toggle_default))
            toggle_value = st.toggle(toggle_label, value=current_value, key=toggle_key)

        with refresh_col:
            if st.button("🔄", key=refresh_key, use_container_width=True, help="Aggiorna"):
                if refresh_callback is not None:
                    refresh_callback()
                else:
                    st.rerun()

        with back_col:
            if st.button("← Cockpit", key=back_key, use_container_width=True):
                _go_to_cockpit(back_target)

    return bool(toggle_value)
