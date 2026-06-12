from pathlib import Path
from urllib.parse import quote

import streamlit as st

from utils.portfolio_calculations import enrich_portfolio_df, portfolio_totals
from utils.portfolio_formatting import fmt_eur, fmt_num, fmt_pct, fmt_qty, value_class
from utils.portfolio_prices import refresh_portfolio_quotes
from utils.portfolio_render import (
    render_portfolio_summary,
    render_portfolio_table_header,
    render_position_values,
    render_row_separator,
)
from utils.portfolio_simulator import calculate_budget_capacity, calculate_buy_simulation
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
DATA_PATH = BASE_DIR / "portfolio" / "portafoglio.json"
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
        "portfolio_simulation_index": None,
        "portfolio_quotes_refreshed_on_load": False,
        "portfolio_last_auto_refresh_result": None,
        "portfolio_storage_mode": "locale",
        "portfolio_last_github_error": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_edit_state() -> None:
    st.session_state["portfolio_edit_index"] = None


def reset_delete_state() -> None:
    st.session_state["portfolio_delete_index"] = None


def reset_simulation_state() -> None:
    st.session_state["portfolio_simulation_index"] = None


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
            "i valori già presenti nel JSON:"
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


def render_persistence_note() -> None:
    storage_mode = st.session_state.get("portfolio_storage_mode", "locale")
    last_error = st.session_state.get("portfolio_last_github_error", "")

    if storage_mode == "github":
        title = "Modalità GitHub API"
        text = "Le modifiche del portafoglio vengono salvate in portfolio/portafoglio.json sulla branch data-watchlists."
    elif storage_mode == "locale_fallback":
        title = "Modalità locale fallback"
        text = "GitHub API non disponibile: modifiche salvate localmente e non persistenti dopo reboot."
        if last_error:
            text += " Ultimo errore: " + str(last_error)
    else:
        title = "Modalità JSON locale"
        text = "GitHub API non configurata: modifiche salvate localmente e non persistenti dopo reboot."

    note_html = (
        '<div class="portfolio-persistence-note">'
        f'<div class="portfolio-persistence-title">{title}</div>'
        f'<div class="portfolio-persistence-text">{text}</div>'
        '</div>'
    )
    st.markdown(note_html, unsafe_allow_html=True)


def render_top_actions() -> None:
    """Render top navigation/actions using WatchlistTradingView-like modern buttons."""
    st.markdown('<div class="portfolio-top-actions-modern">', unsafe_allow_html=True)
    col_refresh, col_back, col_spacer = st.columns([0.48, 1.45, 8.07])

    with col_refresh:
        if st.button("🔄", key="portfolio_refresh_quotes", help="Aggiorna quotazioni"):
            with st.spinner("Aggiornamento quotazioni in corso..."):
                result = refresh_portfolio_quotes(DATA_PATH)

            st.session_state["portfolio_last_auto_refresh_result"] = result
            st.session_state["portfolio_quotes_refreshed_on_load"] = True

            if result["updated"] > 0:
                st.success(f"Quotazioni aggiornate: {result['updated']} su {result['total']}.")
            else:
                st.warning("Nessuna quotazione aggiornata. Mantengo i valori manuali presenti nel JSON.")

            render_refresh_details(result)
            st.rerun()

    with col_back:
        if st.button("← Cockpit", key="portfolio_back_to_cockpit", use_container_width=True):
            go_to_cockpit()

    st.markdown('</div>', unsafe_allow_html=True)


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
    """Return row by original JSON index after display sorting."""
    if original_index not in df.index:
        return None
    return df.loc[original_index]


def _money(value: float, currency: str) -> str:
    suffix = f" {str(currency or '').upper()}" if currency else ""
    return f"{fmt_eur(value)}{suffix}"


def _sim_card(label: str, value: str, css_class: str = "") -> None:
    html = (
        f'<div class="portfolio-sim-card {css_class}">'
        f'<div class="portfolio-sim-card-label">{label}</div>'
        f'<div class="portfolio-sim-card-value">{value}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _adjust_sim_qty(key: str, delta: int, minimum: int, maximum: int) -> None:
    current_value = int(st.session_state.get(key, 0) or 0)
    st.session_state[key] = max(minimum, min(maximum, current_value + delta))


def render_buy_simulator(df) -> None:
    simulation_index = st.session_state.get("portfolio_simulation_index")

    if simulation_index is None:
        return

    row = _get_row_by_original_index(df, simulation_index)
    if row is None:
        reset_simulation_state()
        return

    currency = str(row.get("valuta", "")).upper()
    fx_eur = float(row.get("fx_eur", 1.0) or 1.0)
    title = str(row.get("titolo", ""))
    ticker = str(row.get("ticker", ""))
    market = str(row.get("mercato", ""))

    header_html = (
        '<div class="portfolio-simulator-box">'
        '<div class="portfolio-simulator-kicker">Simulatore posizione</div>'
        f'<div class="portfolio-simulator-title">🧮 Simula acquisto aggiuntivo — {title}</div>'
        f'<div class="portfolio-simulator-subtitle">{market}:{ticker} · valuta {currency} · simulazione non operativa</div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    current_qty = float(row.get("quantita", 0.0) or 0.0)
    current_avg_price = float(row.get("prezzo_medio", 0.0) or 0.0)
    current_market_price = float(row.get("prezzo_mercato", 0.0) or 0.0)

    input_col_1, input_col_2, input_col_3 = st.columns([1.2, 1.2, 1.4])

    with input_col_1:
        buy_price = st.number_input(
            f"Prezzo ipotetico di acquisto ({currency})",
            min_value=0.0,
            value=round(float(current_market_price), 2),
            step=0.01,
            format="%.2f",
            key=f"portfolio_sim_buy_price_{simulation_index}",
        )

    with input_col_2:
        budget = st.number_input(
            f"Budget massimo opzionale ({currency})",
            min_value=0.0,
            value=0.0,
            step=100.0,
            format="%.2f",
            key=f"portfolio_sim_budget_{simulation_index}",
            help="Se valorizzato, il simulatore calcola quante azioni puoi comprare con quel budget.",
        )

    budget_capacity = calculate_budget_capacity(budget, buy_price)
    suggested_max = max(10, int(current_qty), int(budget_capacity["buyable_qty"]), 100)
    slider_max = min(max(suggested_max * 2, 100), 10000)

    slider_key = f"portfolio_sim_add_qty_{simulation_index}"

    if slider_key not in st.session_state:
        st.session_state[slider_key] = 0

    st.session_state[slider_key] = max(
        0,
        min(int(slider_max), int(st.session_state.get(slider_key, 0) or 0)),
    )

    with input_col_3:
        st.markdown('<div class="portfolio-sim-stepper-label">Regola quantità</div>', unsafe_allow_html=True)
        step_cols = st.columns(4, gap="small")
        step_buttons = [(-10, "−10"), (-1, "−1"), (1, "+1"), (10, "+10")]

        for step_col, (delta, label) in zip(step_cols, step_buttons):
            with step_col:
                if st.button(label, key=f"portfolio_sim_step_{simulation_index}_{label}", use_container_width=True):
                    _adjust_sim_qty(slider_key, delta, 0, int(slider_max))
                    st.rerun()

        add_qty = st.slider(
            "Azioni/quote da aggiungere",
            min_value=0,
            max_value=int(slider_max),
            step=1,
            key=slider_key,
        )

    sim = calculate_buy_simulation(
        current_qty=current_qty,
        current_avg_price=current_avg_price,
        current_market_price=current_market_price,
        add_qty=add_qty,
        buy_price=buy_price,
        fx_eur=fx_eur,
    )

    card_cols = st.columns(4)
    with card_cols[0]:
        _sim_card("Azioni aggiunte", fmt_qty(sim["add_qty"]))
    with card_cols[1]:
        _sim_card("Importo ordine", _money(sim["additional_cost"], currency), "portfolio-sim-accent")
    with card_cols[2]:
        _sim_card("Importo ordine EUR", f"{fmt_eur(sim['additional_cost_eur'])} EUR")
    with card_cols[3]:
        _sim_card("Nuova quantità", fmt_qty(sim["new_qty"]))

    card_cols_2 = st.columns(4)
    with card_cols_2[0]:
        _sim_card("Nuovo prezzo medio", _money(sim["new_avg_price"], currency))
    with card_cols_2[1]:
        _sim_card("Capitale totale", _money(sim["new_total_cost"], currency))
    with card_cols_2[2]:
        _sim_card("Valore mercato stimato", f"{fmt_eur(sim['new_market_value_eur'])} EUR")
    with card_cols_2[3]:
        gain_class = value_class(sim["estimated_gain"])
        _sim_card(
            "Guadagno stimato",
            f"{_money(sim['estimated_gain'], currency)} · {fmt_pct(sim['estimated_gain_pct'])}",
            gain_class,
        )

    if budget > 0:
        note_html = (
            '<div class="portfolio-sim-budget-note">'
            f'Con un budget di <b>{_money(budget, currency)}</b> puoi comprare circa '
            f'<b>{fmt_qty(budget_capacity["buyable_qty"])}</b> azioni/quote a {fmt_num(buy_price, 2)} {currency}. '
            f'Budget usato: <b>{_money(budget_capacity["used_budget"], currency)}</b> · '
            f'residuo: <b>{_money(budget_capacity["remaining_budget"], currency)}</b>.'
            '</div>'
        )
        st.markdown(note_html, unsafe_allow_html=True)

    st.caption("Simulazione informativa: non modifica il portafoglio e non rappresenta un consiglio finanziario.")

    close_col, _ = st.columns([1, 6])
    with close_col:
        if st.button("Chiudi simulatore", key=f"portfolio_close_sim_{simulation_index}"):
            reset_simulation_state()
            st.rerun()


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
            action_cols = st.columns([1, 1, 1, 1], gap="small")

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
                if st.button("🧮", key=f"portfolio_sim_{idx}", help="Simula acquisto aggiuntivo"):
                    st.session_state["portfolio_simulation_index"] = idx
                    st.session_state["portfolio_edit_index"] = None
                    st.session_state["portfolio_delete_index"] = None
                    st.rerun()

            with action_cols[2]:
                if st.button("✏️", key=f"portfolio_edit_{idx}", help="Modifica posizione"):
                    st.session_state["portfolio_edit_index"] = idx
                    st.session_state["portfolio_delete_index"] = None
                    st.session_state["portfolio_simulation_index"] = None
                    st.rerun()

            with action_cols[3]:
                if st.button("🗑️", key=f"portfolio_delete_{idx}", help="Elimina posizione"):
                    st.session_state["portfolio_delete_index"] = idx
                    st.session_state["portfolio_edit_index"] = None
                    st.session_state["portfolio_simulation_index"] = None
                    st.rerun()

        render_row_separator()


def sort_portfolio_for_display(df):
    """Sort portfolio by gain descending while preserving original JSON indexes."""
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

    render_persistence_note()

    totals = portfolio_totals(df)
    render_portfolio_summary(totals)

    if df.empty:
        st.info("Il portafoglio è vuoto. Aggiungi la prima posizione.")
        return

    df_display = sort_portfolio_for_display(df)

    render_portfolio_rows(df_display)
    render_buy_simulator(df_display)
    render_edit_form(df_display)
    render_delete_confirmation(df_display)


if __name__ == "__main__":
    main()
