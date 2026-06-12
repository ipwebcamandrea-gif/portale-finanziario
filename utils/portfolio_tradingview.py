
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components


def build_tradingview_symbol(mercato: str, ticker: str) -> str:
    """Build a TradingView symbol such as NASDAQ:MSFT or MIL:ENEL."""
    clean_market = str(mercato or "").strip().upper()
    clean_ticker = str(ticker or "").strip().upper()

    if not clean_market:
        clean_market = "NASDAQ"

    return f"{clean_market}:{clean_ticker}"


def render_tradingview_chart(symbol: str) -> None:
    """Render the selected TradingView chart inside the Streamlit page."""
    if not symbol:
        return

    encoded_symbol = quote(symbol, safe=":")
    tv_url = f"https://www.tradingview.com/chart/?symbol={encoded_symbol}"

    st.markdown(
        f"""
        <div class="portfolio-tv-title">
            Grafico TradingView - {symbol}
        </div>
        """,
        unsafe_allow_html=True,
    )

    components.iframe(
        src=tv_url,
        height=720,
        scrolling=True,
    )
