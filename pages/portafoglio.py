from pathlib import Path
from urllib.parse import quote

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

try:
    from utils.symbols import url_tradingview as watchlist_url_tradingview
except Exception:
    watchlist_url_tradingview = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "portafoglio.csv"
CSS_PATH = BASE_DIR / "css" / "portafoglio.css"
COCKPIT_PAGE = "main.py"
AUTO_REFRESH_QUOTES_ON_FIRST_LOAD = True


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
        "portfolio_quotes_refreshed_on_load": False,
        "portfolio_last_auto_refresh_result": None,
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


def portfolio_tradingview_url(
    mercato: str,
    ticker: str,
    tv_symbol: str = "",
    valuta: str = "",
) -> str:
    """Return the same TradingView external URL style used by WatchlistTradingView."""
    symbol = build_tradingview_symbol(mercato, ticker, tv_symbol, valuta)

    if watchlist_url_tradingview is not None:
        try:
            return watchlist_url_tradingview(symbol)
        except Exception:
            pass

    encoded_symbol = quote(symbol, safe=":")
    return f"https://www.tradingview.com/chart/?symbol={encoded_symbol}"


def auto_refresh_quotes_once() -> None:
    if not AUTO_REFRESH_QUOTES_ON_FIRST_LOAD:
        return

    if st.session_state.get("portfolio_quotes_refreshed_on_load", False):
        return

    st.session_state["portfolio_quotes_refreshed_on_load"] = True

    with st.spinner("Aggiornamento automatico quotazioni in corso..."):
        result = refresh_portfolio_quotes(DATA_PATH)

    st.session_state["portfolio_last_auto_refresh_result"] = result


def render_refresh_details(result: dict) -> None:
    """Show details about quote refresh failures, if any."""
    failed = result.get("failed", []) or []

    if not failed:
        return

    with st.expander("Dettaglio quotazioni non aggiornate", expanded=False):
        st.write(
            "Questi simboli non sono stati aggiornati da yfinance e quindi mantengono "
            "i valori già presenti nel CSV:"
        )
        for item in failed:
            st.write(f"- {item}")


def render_auto_refresh_status() -> None:
    result = st.session_state.get("portfolio_last_auto_refresh_result")

    if not result:
        return

    updated = result.get("updated", 0)
    total = result.get("total", 0)

    if updated > 0:
        st.caption(f"Quotazioni aggiornate automaticamente/all'ultimo refresh: {updated} su {total}.")
    else:
        st.caption("Aggiornamento eseguito: nessuna quotazione aggiornata, valori manuali mantenuti.")

    render_refresh_details(result)


def render_top_actions() -> None:
    col_back, col_refresh, col_spacer = st.columns([1.0, 1.35, 7.65])

    with col_back:
        if st.button("← Cockpit", key="portfolio_back_to_cockpit"):
            go_to_cockpit()

    with col_refresh:
        if st.button("🔄 Aggiorna quotazioni", key="portfolio_refresh_quotes"):
            with st.spinner("Aggiornamento quotazioni in corso..."):
                result = refresh_portfolio_quotes(DATA_PATH)

            st.session_state["portfolio_last_auto_refresh_result"] = result
            st.session_state["portfolio_quotes_refreshed_on_load"] = True

            if result["updated"] > 0:
                st.success(f"Quotazioni aggiornate: {result['updated']} su {result['total']}.")
            else:
                st.warning("Nessuna quotazione aggiornata. Mantengo i valori manuali presenti nel CSV.")

            render_refresh_details(result)
            st.rerun()


def render_add_form() -> None:
    with st.expander("➕ Aggiungi posizione", expanded=False):
        with st.form("portfolio_add_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            col4, col5, col6, col7 = st.columns(4)
            col8, col9 = st.columns(2)

            with col1:
                ticker = st.text_input("Ticker", placeholder="MSFT oppure 1MSFT")

            with col2:
                titolo = st.text_input("Titolo", placeholder="MICROSOFT")

            with col3:
                mercato = st.text_input("Mercato TradingView", value="NASDAQ", help="Esempio: NASDAQ, NYSE, MIL")

            with col4:
                valuta = st.selectbox("Valuta", ["EUR", "USD", "GBP", "CHF"])

            with col5:
                quantita = st.number_input("Quantità", min_value=0.0, step=1.0, format="%.6f")

            with col6:
                prezzo_medio = st.number_input("P.zo medio carico", min_value=0.0, step=0.01, format="%.6f")

            with col7:
                prezzo_mercato = st.number_input("P.zo mercato", min_value=0.0, step=0.01, format="%.6f")

            with col8:
                yf_symbol = st.text_input(
                    "Simbolo yfinance opzionale",
                    placeholder="1MSFT.MI",
                    help="Da usare se la posizione è quotata su mercato diverso dal ticker principale, es. EUR su Borsa Italiana.",
                )

            with col9:
                tv_symbol = st.text_input(
                    "Simbolo TradingView opzionale",
                    placeholder="MIL:1MSFT",
                    help="Da usare se il grafico deve aprire uno specifico mercato/strumento.",
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
                        "strumento": "",
                        "valuta": valuta,
                        "quantita": quantita,
                        "prezzo_medio": prezzo_medio,
                        "prezzo_mercato": prezzo_mercato,
                        "prezzo_precedente": prezzo_precedente,
                        "yf_symbol": yf_symbol.upper().strip(),
                        "tv_symbol": tv_symbol.upper().strip(),
                    },
                )

                st.success("Posizione aggiunta.")
                st.rerun()


def _get_row_by_original_index(df, original_index: int):
    """Return row by original CSV index after display sorting."""
    if original_index not in df.index:
        return None
    return df.loc[original_index]


def render_edit_form(df) -> None:
    edit_index = st.session_state.get("portfolio_edit_index")

    if edit_index is None:
        return

    row = _get_row_by_original_index(df, edit_index)
    if row is None:
        reset_edit_state()
        return

    st.markdown('<div class="portfolio-form-box">', unsafe_allow_html=True)
    st.subheader(f"✏️ Modifica posizione: {row['titolo']}")

    with st.form(f"portfolio_edit_form_{edit_index}"):
        col1, col2, col3 = st.columns(3)
        col4, col5, col6, col7 = st.columns(4)
        col8, col9 = st.columns(2)

        with col1:
            ticker = st.text_input("Ticker", value=row["ticker"])

        with col2:
            titolo = st.text_input("Titolo", value=row["titolo"])

        with col3:
            mercato = st.text_input("Mercato TradingView", value=row["mercato"])

        with col4:
            valute = ["EUR", "USD", "GBP", "CHF"]
            current_valuta_index = valute.index(row["valuta"]) if row["valuta"] in valute else 0
            valuta = st.selectbox("Valuta", valute, index=current_valuta_index)

        with col5:
            quantita = st.number_input("Quantità", min_value=0.0, value=float(row["quantita"]), step=1.0, format="%.6f")

        with col6:
            prezzo_medio = st.number_input("P.zo medio carico", min_value=0.0, value=float(row["prezzo_medio"]), step=0.01, format="%.6f")

        with col7:
            prezzo_mercato = st.number_input("P.zo mercato", min_value=0.0, value=float(row["prezzo_mercato"]), step=0.01, format="%.6f")

        with col8:
            yf_symbol = st.text_input("Simbolo yfinance opzionale", value=row.get("yf_symbol", ""))

        with col9:
            tv_symbol = st.text_input("Simbolo TradingView opzionale", value=row.get("tv_symbol", ""))

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
                    "strumento": "",
                    "valuta": valuta,
                    "quantita": quantita,
                    "prezzo_medio": prezzo_medio,
                    "prezzo_mercato": prezzo_mercato,
                    "prezzo_precedente": prezzo_precedente,
                    "yf_symbol": yf_symbol.upper().strip(),
                    "tv_symbol": tv_symbol.upper().strip(),
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

    row = _get_row_by_original_index(df, delete_index)
    if row is None:
        reset_delete_state()
        return

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
                st.link_button(
                    "📊",
                    portfolio_tradingview_url(
                        row["mercato"],
                        row["ticker"],
                        row.get("tv_symbol", ""),
                        row.get("valuta", ""),
                    ),
                    use_container_width=True,
                    help="Apri TradingView esterno",
                )

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


def sort_portfolio_for_display(df):
    """Sort portfolio by gain descending while preserving original CSV indexes."""
    if df.empty or "var_da_carico_eur" not in df.columns:
        return df

    return df.sort_values(
        by="var_da_carico_eur",
        ascending=False,
        na_position="last",
        kind="mergesort",
    )


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

    auto_refresh_quotes_once()
    render_auto_refresh_status()

    df = load_portfolio(DATA_PATH)
    df = enrich_portfolio_df(df)

    totals = portfolio_totals(df)
    render_portfolio_summary(totals)

    if df.empty:
        st.info("Il portafoglio è vuoto. Aggiungi la prima posizione.")
        return

    df_display = sort_portfolio_for_display(df)

    render_portfolio_rows(df_display)
    render_edit_form(df_display)
    render_delete_confirmation(df_display)


if __name__ == "__main__":
    main()
