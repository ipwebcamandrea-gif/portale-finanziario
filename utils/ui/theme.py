from __future__ import annotations

import streamlit as st


def apply_dark_theme_mobile() -> None:
    """Force the dark visual base and shared topbar style on mobile.

    This function is injected after page CSS, so it also fixes pages whose local
    styles override Streamlit buttons differently on mobile.
    """

    st.markdown(
        """
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

            div[class*="st-key-"][class*="_back"] .stButton > button,
            div[class*="st-key-"][class*="_refresh"] .stButton > button,
            div[class*="st-key-"][class*="_back"] button,
            div[class*="st-key-"][class*="_refresh"] button,
            div[class*="st-key-"][class*="_back"] a,
            div[class*="st-key-"][class*="_refresh"] a {
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
        """,
        unsafe_allow_html=True,
    )
