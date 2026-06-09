import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


# =========================
# PROTEZIONE LOGIN
# =========================

if not st.session_state.get("authenticated", False):
    st.error("Accesso non autorizzato.")

    if st.button("Torna al Login"):
        st.switch_page("main.py")

    st.stop()


# =========================
# CONFIGURAZIONE FILE / CSS
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent
GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
GRAFICO_TV_CSS = ROOT_DIR / "css" / "grafico_tradingview.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(
                "<style>" + file.read() + "</style>",
                unsafe_allow_html=True
            )


local_css(GLOBAL_CSS)
local_css(GRAFICO_TV_CSS)


# =========================
# HELPERS
# =========================

def simbolo_tradingview(symbol):
    """
    Conversione pratica Yahoo Finance -> TradingView.

    Nota:
    Per alcuni titoli USA TradingView può mostrare comunque la dicitura dati "Cboe One".
    Quella dicitura riguarda il feed dati usato dal widget, non necessariamente il mercato
    di quotazione richiesto. Qui forziamo comunque il simbolo TradingView esplicito.
    """
    symbol = str(symbol or "").strip().upper()

    if not symbol:
        return "NASDAQ:AAPL"

    if ":" in symbol:
        return symbol

    if symbol.endswith(".MI"):
        return "MIL:" + symbol.replace(".MI", "")

    nasdaq_symbols = {
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "NFLX", "ADBE",
        "AMD", "INTC", "CSCO", "AVGO", "QCOM", "TXN", "PEP", "COST", "AMAT", "MU",
        "PYPL", "SBUX", "ISRG", "BKNG", "LRCX", "PANW", "CRWD", "SHOP", "ARM", "SMCI"
    }

    nyse_symbols = {
        "JPM", "BAC", "V", "MA", "BRK.B", "BRK.A", "KO", "PG", "JNJ", "UNH", "HD",
        "DIS", "IBM", "ORCL", "CRM", "CVX", "XOM", "WMT", "MCD", "NKE", "CAT",
        "BA", "GS", "MS", "AXP", "GE", "T", "VZ", "PFE", "MRK", "LLY"
    }

    if symbol in nasdaq_symbols:
        return "NASDAQ:" + symbol

    if symbol in nyse_symbols:
        return "NYSE:" + symbol

    # Default operativo: molti ticker tech USA sono su NASDAQ.
    return "NASDAQ:" + symbol


def bottone_torna_watchlist():
    with st.container(key="grafico_tv_back_watchlist"):
        if st.button(
            "← Watchlist",
            key="grafico_tv_back_btn",
            use_container_width=True,
            help="Torna alla Watchlist TradingView"
        ):
            st.switch_page("pages/watchlist_tradingview.py")


def tradingview_widget_html(tv_symbol):
    config = {
        "autosize": True,
        "symbol": tv_symbol,
        "interval": "W",
        # 120M = circa 10 anni. Evita il comportamento di ALL che può portare il widget a visualizzare 1M.
        "range": "120M",
        "timezone": "Europe/Rome",
        "theme": "dark",
        "style": "1",
        "locale": "it",
        "backgroundColor": "#0e1117",
        "gridColor": "rgba(255, 255, 255, 0.06)",
        "allow_symbol_change": True,
        "calendar": False,
        "details": False,
        "hide_side_toolbar": False,
        "hide_top_toolbar": False,
        "hide_legend": False,
        "hide_volume": False,
        "hotlist": False,
        "withdateranges": True,
        "save_image": True,
        "support_host": "https://www.tradingview.com",
        "studies": [
            {
                "id": "MAWeighted@tv-basicstudies",
                "inputs": {"length": 21},
                "overrides": {
                    "plot.color": "#ffffff",
                    "plot.linewidth": 2
                }
            },
            {
                "id": "MAWeighted@tv-basicstudies",
                "inputs": {"length": 50},
                "overrides": {
                    "plot.color": "#26a69a",
                    "plot.linewidth": 2
                }
            },
            {
                "id": "MAExp@tv-basicstudies",
                "inputs": {"length": 200},
                "overrides": {
                    "plot.color": "#ffeb3b",
                    "plot.linewidth": 2
                }
            },
            {
                "id": "MASimple@tv-basicstudies",
                "inputs": {"length": 200},
                "overrides": {
                    "plot.color": "#ff9800",
                    "plot.linewidth": 2
                }
            }
        ],
        "studies_overrides": {
            "moving average weighted.ma.color": "#ffffff",
            "moving average weighted.ma.linewidth": 2,
            "moving average exponential.ma.color": "#ffeb3b",
            "moving average exponential.ma.linewidth": 2,
            "moving average.ma.color": "#ff9800",
            "moving average.ma.linewidth": 2
        }
    }

    config_json = json.dumps(config, ensure_ascii=False, indent=8)

    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8" />
            <style>
                html, body {{
                    height: 100%;
                    width: 100%;
                    margin: 0;
                    padding: 0;
                    background: #0e1117;
                    overflow: hidden;
                }}
                .tradingview-widget-container {{
                    height: 100%;
                    width: 100%;
                    background: #0e1117;
                }}
                .tradingview-widget-container__widget {{
                    height: 100%;
                    width: 100%;
                }}
            </style>
        </head>
        <body>
            <div class="tradingview-widget-container">
                <div class="tradingview-widget-container__widget"></div>
                <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
                {config_json}
                </script>
            </div>
        </body>
    </html>
    """


# =========================
# PAGE
# =========================

ticker_raw = st.session_state.get("ticker_selezionato_tv")

if not ticker_raw:
    st.warning("Nessun ticker selezionato. Apri questa pagina dalla Watchlist TradingView usando il pulsante 📊.")
    bottone_torna_watchlist()
    st.stop()

tv_symbol = simbolo_tradingview(ticker_raw)

header_col_1, header_col_2 = st.columns([5.0, 1.25], vertical_alignment="center")

with header_col_1:
    st.empty()

with header_col_2:
    bottone_torna_watchlist()

st.markdown('<div class="grafico-tv-shell">', unsafe_allow_html=True)
components.html(
    tradingview_widget_html(tv_symbol),
    height=1040,
    scrolling=False
)
st.markdown('</div>', unsafe_allow_html=True)
