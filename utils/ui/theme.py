from __future__ import annotations

import streamlit as st


_TOPBAR_DARK_MOBILE_CSS = """
<style>
@media screen and (max-width: 768px) {
    html,
    body,
    [data-testid="stAppViewContainer"] {
        background-color: #0d1117 !important;
        color: #e6edf3 !important;
    }

    [data-testid="stAppViewContainer"] > .main,
    .main,
    .block-container {
        background: transparent !important;
    }

    div[class*="st-key-portfolio_mobile_view_back"] button,
    div[class*="st-key-portfolio_mobile_view_refresh"] button,
    div[class*="st-key-allocation_mobile_view_back"] button,
    div[class*="st-key-allocation_mobile_view_refresh"] button,
    div[class*="st-key-watchlist_tv_mobile_view_back"] button,
    div[class*="st-key-watchlist_tv_mobile_view_refresh"] button {
        min-height: 38px !important;
        height: 38px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(0, 176, 255, 0.42) !important;
        background:
            radial-gradient(circle at top left, rgba(0, 176, 255, 0.18), transparent 36%),
            linear-gradient(180deg, #202733 0%, #151b24 100%) !important;
        color: #e6edf3 !important;
        font-weight: 950 !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.05),
            0 0 14px rgba(0, 176, 255, 0.10) !important;
    }
}
</style>
"""


def apply_dark_theme_mobile() -> None:
    """Force dark mobile theme and shared topbar style across pages."""
    st.markdown(_TOPBAR_DARK_MOBILE_CSS, unsafe_allow_html=True)
