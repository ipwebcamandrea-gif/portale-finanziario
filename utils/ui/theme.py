
from __future__ import annotations

import streamlit as st


def apply_dark_theme_mobile() -> None:
    """Force the dark visual base on mobile without changing desktop layout."""

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
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
