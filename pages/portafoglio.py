from pathlib import Path

import streamlit as st

from utils.portfolio_calculations import enrich_portfolio_df, portfolio_totals
from utils.portfolio_prices import refresh_portfolio_quotes
from utils.portfolio_render import (
    render_portfolio_summary,
    render_portfolio_table_header,
    render_position_values,
    render_row_separator,
)
from utils.portfolio_storage import (
    add_position,
    delete_position,
    load_portfolio,
    update_position,
)
from utils.portfolio_tradingview import build_tradingview_symbol


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "portafoglio.csv"
CSS_PATH = BASE_DIR / "css" / "portafoglio.css"
COCKPIT_PAGE = "main.py"
TRADINGVIEW_PAGE = "pages/grafico_tradingview.py"


st.set_page_config(
    page_title="Portafoglio",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_css() -> None:
    if CSS_PATH.exists():
        st.markdown(
            f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def init_state() -> None:
    defaults = {
        "portfolio_edit_index": None,
        "portfolio_delete_index": None,
        "portfolio_selected_symbol": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_edit_state() -> None:
    st.session_state["portfolio_edit_index"] = None


def reset_delete_state() -> None:
    st.session_state["portfolio_delete_index"] = None


def go_to_cockpit() -> None:
    try:
        st.switch_page(COCKPIT_PAGE)
    except Exception:
        st.warning(
            f"Non riesco ad aprire {COCKPIT_PAGE}. Se il cockpit ha un nome diverso, modifica COCKPIT_PAGE in pages/portafoglio.py."
        )


def _split_tradingview_symbol(symbol: str) -> tuple[str, str]:
    clean_symbol = str(symbol or "").strip().upper()
    if ":" in clean_symbol:
        market, ticker = clean_symbol.split(":", 1)
        return market.strip(), ticker.strip()
    return "", clean_symbol


def set_tradingview_session_state(symbol: str) -> None:
    """Set all known/likely session keys used by TradingView pages.

    La pagina WatchlistTradingView esistente può leggere una chiave specifica.
    Per evitare rotture, da Portafoglio valorizziamo sia le chiavi generiche
    sia quelle con prefisso watchlist/tradingview/portfolio.
    """
    market, ticker = _split_tradingview_symbol(symbol)

    symbol_keys = [
        "portfolio_selected_symbol",
        "selected_tradingview_symbol",
        "tradingview_symbol",
        "tv_symbol",
        "selected_symbol",
        "symbol",
        "current_symbol",
        "chart_symbol",
        "selected_tv_symbol",
        "tv_selected_symbol",
        "watchlist_selected_symbol",
        "watchlist_tradingview_symbol",
        "watchlist_tv_symbol",
        "watchlist_chart_symbol",
        "selected_watchlist_symbol",
        "selected_watchlist_tradingview_symbol",
    ]

    ticker_keys = [
        "selected_ticker",
        "ticker",
        "current_ticker",
        "chart_ticker",
        "tv_ticker",
        "selected_tv_ticker",
        "tradingview_ticker",
        "selected_tradingview_ticker",
        "watchlist_selected_ticker",
        "watchlist_ticker",
        "watchlist_tv_ticker",
        "watchlist_chart_ticker",
        "selected_watchlist_ticker",
    ]

    market_keys = [
        "selected_market",
        "market",
        "mercato",
        "selected_mercato",
        "tv_market",
        "tradingview_market",
        "watchlist_market",
    ]

    for key in symbol_keys:
        st.session_state[key] = symbol

    for key in ticker_keys:
        st.session_state[key] = ticker

    for key in market_keys:
        st.session_state[key] = market

    st.session_state["tradingview_source"] = "portfolio"
    st.session_state["chart_source"] = "portfolio"
    st.session_state["opened_from_watchlist_tradingview"] = True
    st.session_state["opened_from_portfolio"] = True


def open_tradingview_page(symbol: str) -> None:
    """Open the app TradingView page with the selected symbol."""
    if not symbol:
        st.warning("Simbolo TradingView non valido.")
        return

    set_tradingview_session_state(symbol)

    try:
        st.switch_page(TRADINGVIEW_PAGE)
    except Exception:
        st.error(
            f"Non riesco ad aprire {TRADINGVIEW_PAGE}. Controlla il nome reale del file pagina e modifica TRADINGVIEW_PAGE in pages/portafoglio.py."
        )
        st.link_button(
            "Apri su TradingView ↗",
            url=f"https://www.tradingview.com/chart/?symbol={symbol}",
        )


def render_top_actions() -> None:
    col_back, col_refresh, col_spacer = st.columns([1.0, 1.35, 7.65])

    with col_back:
        if st.button("← Cockpit", key="portfolio_back_to_cockpit"):
            go_to_cockpit()

    with col_refresh:
        if st.button("🔄 Aggiorna quotazioni", key="portfolio_refresh_quotes"):
            with st.spinner("Aggiornamento quotazioni in corso..."):
                result = refresh_portfolio_quotes(DATA_PATH)

            if result["updated"] > 0:
                st.success(f"Quotazioni aggiornate: {result['updated']} su {result['total']}.")
            else:
                st.warning("Nessuna quotazione aggiornata. Mantengo i valori manuali presenti nel CSV.")

            if result["failed"]:
                with st.expander("Dettaglio quotazioni non aggiornate", expanded=False):
                    for item in result["failed"]:
                        st.write(f"- {item}")

            st.rerun()


def render_add_form() -> None:
    with st.expander("➕ Aggiungi posizione", expanded=False):
        with st.form("portfolio_add_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            col4, col5, col6, col7, col8 = st.columns(5)

            with col1:
                ticker = st.text_input("Ticker", placeholder="MSFT")

            with col2:
                titolo = st.text_input("Titolo", placeholder="MICROSOFT")

            with col3:
                mercato = st.text_input("Mercato TradingView", value="NASDAQ")

            with col4:
                strumento = st.selectbox(
                    "Strumento",
                    ["Azione", "ETF", "ETC", "Obbligazione", "Crypto", "Altro"],
                )

            with col5:
                valuta = st.selectbox("Valuta", ["EUR", "USD", "GBP", "CHF"])

            with col6:
                quantita = st.number_input(
                    "Quantità",
                    min_value=0.0,
                    step=1.0,
                    format="%.6f",
                )

            with col7:
                prezzo_medio = st.number_input(
                    "P.zo medio carico",
                    min_value=0.0,
                    step=0.01,
                    format="%.6f",
                )

            with col8:
                prezzo_mercato = st.number_input(
                    "P.zo mercato",
                    min_value=0.0,
                    step=0.01,
                    format="%.6f",
                )

            prezzo_precedente = st.number_input(
                "P.zo precedente",
                min_value=0.0,
                step=0.01,
                format="%.6f",
                help="Valore manuale usato come fallback se l'aggiornamento quote non trova dati live.",
            )

            submitted = st.form_submit_button("Aggiungi posizione")

            if submitted:
                if not ticker.strip() or not titolo.strip():
                    st.warning("Ticker e Titolo sono obbligatori.")
                    return

                add_position(
                    DATA_PATH,
                    {
                        "ticker": ticker.upper().strip(),
                        "titolo": titolo.strip(),
                        "mercato": mercato.upper().strip(),
                        "strumento": strumento,
                        "valuta": valuta,
                        "quantita": quantita,
                        "prezzo_medio": prezzo_medio,
                        "prezzo_mercato": prezzo_mercato,
                        "prezzo_precedente": prezzo_precedente,
                    },
                )

                st.success("Posizione aggiunta.")
                st.rerun()


def render_edit_form(df) -> None:
    edit_index = st.session_state.get("portfolio_edit_index")

    if edit_index is None:
        return

    if edit_index < 0 or edit_index >= len(df):
        reset_edit_state()
        return

    row = df.iloc[edit_index]

    st.markdown('<div class="portfolio-form-box">', unsafe_allow_html=True)
    st.subheader(f"✏️ Modifica posizione: {row['titolo']}")

    with st.form(f"portfolio_edit_form_{edit_index}"):
        col1, col2, col3 = st.columns(3)
        col4, col5, col6, col7, col8 = st.columns(5)

        with col1:
            ticker = st.text_input("Ticker", value=row["ticker"])

        with col2:
            titolo = st.text_input("Titolo", value=row["titolo"])

        with col3:
            mercato = st.text_input("Mercato TradingView", value=row["mercato"])

        with col4:
            strumenti = ["Azione", "ETF", "ETC", "Obbligazione", "Crypto", "Altro"]
            current_strumento_index = (
                strumenti.index(row["strumento"]) if row["strumento"] in strumenti else 0
            )
            strumento = st.selectbox(
                "Strumento",
                strumenti,
                index=current_strumento_index,
            )

        with col5:
            valute = ["EUR", "USD", "GBP", "CHF"]
            current_valuta_index = valute.index(row["valuta"]) if row["valuta"] in valute else 0
            valuta = st.selectbox("Valuta", valute, index=current_valuta_index)

        with col6:
            quantita = st.number_input(
                "Quantità",
                min_value=0.0,
                value=float(row["quantita"]),
                step=1.0,
                format="%.6f",
            )

        with col7:
            prezzo_medio = st.number_input(
                "P.zo medio carico",
                min_value=0.0,
                value=float(row["prezzo_medio"]),
                step=0.01,
                format="%.6f",
            )

        with col8:
            prezzo_mercato = st.number_input(
                "P.zo mercato",
                min_value=0.0,
                value=float(row["prezzo_mercato"]),
                step=0.01,
                format="%.6f",
            )

        prezzo_precedente = st.number_input(
            "P.zo precedente",
            min_value=0.0,
            value=float(row["prezzo_precedente"]),
            step=0.01,
            format="%.6f",
        )

        col_save, col_cancel = st.columns([1, 5])

        with col_save:
            submitted = st.form_submit_button("Salva")

        with col_cancel:
            cancelled = st.form_submit_button("Annulla")

        if submitted:
            if not ticker.strip() or not titolo.strip():
                st.warning("Ticker e Titolo sono obbligatori.")
                return

            update_position(
                DATA_PATH,
                edit_index,
                {
                    "ticker": ticker.upper().strip(),
                    "titolo": titolo.strip(),
                    "mercato": mercato.upper().strip(),
                    "strumento": strumento,
                    "valuta": valuta,
                    "quantita": quantita,
                    "prezzo_medio": prezzo_medio,
                    "prezzo_mercato": prezzo_mercato,
                    "prezzo_precedente": prezzo_precedente,
                },
            )

            reset_edit_state()
            st.success("Posizione aggiornata.")
            st.rerun()

        if cancelled:
            reset_edit_state()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_delete_confirmation(df) -> None:
    delete_index = st.session_state.get("portfolio_delete_index")

    if delete_index is None:
        return

    if delete_index < 0 or delete_index >= len(df):
        reset_delete_state()
        return

    row = df.iloc[delete_index]

    st.markdown('<div class="portfolio-warning-box">', unsafe_allow_html=True)
    st.warning(f"Confermi l'eliminazione di {row['titolo']} ({row['mercato']}:{row['ticker']})?")

    col_confirm, col_cancel = st.columns([1, 5])

    with col_confirm:
        if st.button("Conferma elimina", key=f"confirm_delete_{delete_index}"):
            delete_position(DATA_PATH, delete_index)
            reset_delete_state()
            st.success("Posizione eliminata.")
            st.rerun()

    with col_cancel:
        if st.button("Annulla", key=f"cancel_delete_{delete_index}"):
            reset_delete_state()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_portfolio_rows(df) -> None:
    render_portfolio_table_header()

    for idx, row in df.iterrows():
        action_col = render_position_values(row)

        with action_col:
            st.markdown('<div class="portfolio-action-spacer"></div>', unsafe_allow_html=True)
            action_cols = st.columns([1, 1, 1], gap="small")

            with action_cols[0]:
                if st.button("📊", key=f"portfolio_chart_{idx}", help="Apri grafico TradingView"):
                    symbol = build_tradingview_symbol(row["mercato"], row["ticker"])
                    open_tradingview_page(symbol)

            with action_cols[1]:
                if st.button("✏️", key=f"portfolio_edit_{idx}", help="Modifica posizione"):
                    st.session_state["portfolio_edit_index"] = idx
                    st.session_state["portfolio_delete_index"] = None
                    st.rerun()

            with action_cols[2]:
                if st.button("🗑️", key=f"portfolio_delete_{idx}", help="Elimina posizione"):
                    st.session_state["portfolio_delete_index"] = idx
                    st.session_state["portfolio_edit_index"] = None
                    st.rerun()

        render_row_separator()


def main() -> None:
    load_css()
    init_state()

    render_top_actions()

    st.markdown('<div class="portfolio-page-title">💼 Portafoglio</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="portfolio-page-subtitle">Gestione posizioni, valori di mercato e grafico TradingView.</div>',
        unsafe_allow_html=True,
    )

    render_add_form()

    df = load_portfolio(DATA_PATH)
    df = enrich_portfolio_df(df)

    totals = portfolio_totals(df)
    render_portfolio_summary(totals)

    if df.empty:
        st.info("Il portafoglio è vuoto. Aggiungi la prima posizione.")
        return

    render_portfolio_rows(df)
    render_edit_form(df)
    render_delete_confirmation(df)


if __name__ == "__main__":
    main()
