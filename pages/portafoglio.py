from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import parse_qs, quote, unquote, urlparse

import streamlit as st

from components.standard_header import render_standard_page_header
from components.ticker_lookup_selector import render_ticker_add_intro, render_ticker_lookup_selector
from utils.auth import require_login
from utils.portfolio_calculations import enrich_portfolio_df, portfolio_totals
from utils.portfolio_formatting import fmt_eur, fmt_num, fmt_pct, fmt_qty, value_class
from utils.portfolio_fx import convert_to_eur
from utils.portfolio_input_formatting import (
    PRICE_INPUT_FORMAT,
    PRICE_INPUT_STEP,
    QTY_INPUT_FORMAT,
    QTY_INPUT_STEP,
    normalize_price,
    normalize_quantity,
)
from utils.portfolio_add_smart import build_smart_position
from utils.portfolio_prices import refresh_portfolio_quotes
from utils.portfolio_render import (
    render_portfolio_summary,
    render_portfolio_table_header,
    render_position_values,
    render_row_separator,
)
from utils.portfolio_simulator import (
    calculate_budget_capacity,
    calculate_buy_simulation,
    calculate_suggested_quantity_from_budget,
)
from utils.portfolio_storage import (
    add_position,
    delete_position,
    load_portfolio,
    update_position,
)
from utils.portfolio_tradingview import build_tradingview_symbol
from utils.portafoglio_mobile.portfolio_mobile_render import (
    render_mobile_portfolio_rows,
    render_mobile_portfolio_summary,
)

try:
    from utils.symbols import url_tradingview as watchlist_url_tradingview
except Exception:
    watchlist_url_tradingview = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "portfolio" / "portafoglio.json"
GLOBAL_CSS_PATH = BASE_DIR / "css" / "global.css"
CSS_PATH = BASE_DIR / "css" / "portafoglio.css"
MOBILE_CSS_PATH = BASE_DIR / "css" / "portafoglio_mobile.css"
COCKPIT_PAGE = "main.py"
AUTO_REFRESH_QUOTES_ON_FIRST_LOAD = True
MANUAL_REFRESH_MODE = True


st.set_page_config(
    page_title="Portafoglio",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)


require_login()

def load_css() -> None:
    for css_path in (GLOBAL_CSS_PATH, CSS_PATH, MOBILE_CSS_PATH):
        if css_path.exists():
            st.markdown(
                f"<style>{css_path.read_text(encoding='utf-8')}</style>",
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
        "portfolio_mobile_view": True,
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




def current_refresh_timestamp() -> str:
    """Return current refresh timestamp in Europe/Rome time."""
    return datetime.now(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y %H:%M:%S")


def set_last_refresh_timestamp() -> None:
    st.session_state["portfolio_last_refresh_timestamp"] = current_refresh_timestamp()


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


def portfolio_tradingview_forecast_url(
    mercato: str,
    ticker: str,
    tv_symbol: str = "",
    valuta: str = "",
) -> str:
    """Return TradingView analyst forecast URL, same logic used in Watchlist."""
    tv_url = portfolio_tradingview_url(mercato, ticker, tv_symbol, valuta)

    try:
        parsed = urlparse(tv_url)
        path_parts = [part for part in parsed.path.split("/") if part]

        if "symbols" in path_parts:
            symbols_index = path_parts.index("symbols")
            if symbols_index + 1 < len(path_parts):
                tv_symbol_path = path_parts[symbols_index + 1].strip()
                if tv_symbol_path:
                    return f"https://www.tradingview.com/symbols/{tv_symbol_path}/forecast/"

        query_symbol = parse_qs(parsed.query).get("symbol", [""])[0]
        query_symbol = unquote(query_symbol).strip()
        if query_symbol:
            tv_symbol_path = query_symbol.replace(":", "-")
            return f"https://www.tradingview.com/symbols/{tv_symbol_path}/forecast/"
    except Exception:
        pass

    return tv_url


def open_portfolio_target_page(row) -> None:
    """Open internal Target Analisti page for a portfolio row."""
    yf_symbol = str(row.get("yf_symbol") or row.get("ticker") or "").strip().upper()
    st.session_state["target_selected"] = {
        "yf_symbol": yf_symbol,
        "ticker": str(row.get("ticker") or yf_symbol).strip().upper(),
        "tv_symbol": str(row.get("tv_symbol") or "").strip().upper(),
        "name": str(row.get("titolo") or row.get("ticker") or yf_symbol).strip(),
        "market": str(row.get("mercato") or "").strip().upper(),
        "currency": str(row.get("valuta") or "").strip().upper(),
        "source": "portfolio",
    }
    st.switch_page("pages/target_analisti.py")


def clear_financial_data_cache() -> None:
    """Force fresh financial data on the next yfinance calls."""
    st.cache_data.clear()


def auto_refresh_quotes_on_page_open() -> None:
    """Refresh portfolio quotes every time the Portafoglio page is opened/rerun.

    The page must never render stale prices from portfolio/portafoglio.json before
    attempting a yfinance refresh. If yfinance fails for one or more symbols,
    refresh_portfolio_quotes keeps the existing JSON values and exposes failures
    in portfolio_last_auto_refresh_result.
    """
    if not AUTO_REFRESH_QUOTES_ON_FIRST_LOAD:
        return

    clear_financial_data_cache()

    with st.spinner("Aggiornamento automatico quotazioni in corso..."):
        result = refresh_portfolio_quotes(DATA_PATH)

    st.session_state["portfolio_last_auto_refresh_result"] = result
    st.session_state["portfolio_quotes_refreshed_on_load"] = True
    set_last_refresh_timestamp()


def is_portfolio_auto_refresh_safe() -> bool:
    """Return True when auto-refresh can run without interrupting inline panels."""
    blocking_keys = (
        "portfolio_edit_index",
        "portfolio_delete_index",
        "portfolio_simulation_index",
    )
    return all(st.session_state.get(key) is None for key in blocking_keys)


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

    refresh_time = st.session_state.get("portfolio_last_refresh_timestamp", "")
    refresh_suffix = f" · Aggiornamento dati: {refresh_time}" if refresh_time else ""

    if updated > 0:
        st.caption(f"Quotazioni aggiornate automaticamente/all'ultimo refresh: {updated} su {total}{refresh_suffix}.")
    else:
        st.caption(f"Aggiornamento eseguito: nessuna quotazione aggiornata, valori manuali mantenuti{refresh_suffix}.")

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


def render_top_actions() -> bool:
    """Render top navigation/actions and return mobile-view flag."""
    st.markdown('<div class="portfolio-top-actions-modern">', unsafe_allow_html=True)
    col_refresh, col_back, col_mobile, col_spacer = st.columns([0.48, 1.45, 1.35, 6.72])

    with col_refresh:
        if st.button("🔄", key="portfolio_refresh_quotes", help="Aggiorna quotazioni"):
            clear_financial_data_cache()

            with st.spinner("Aggiornamento quotazioni in corso..."):
                result = refresh_portfolio_quotes(DATA_PATH)

            st.session_state["portfolio_last_auto_refresh_result"] = result
            st.session_state["portfolio_quotes_refreshed_on_load"] = True
            set_last_refresh_timestamp()

            if result["updated"] > 0:
                st.success(f"Quotazioni aggiornate: {result['updated']} su {result['total']}.")
            else:
                st.warning("Nessuna quotazione aggiornata. Mantengo i valori manuali presenti nel JSON.")

            render_refresh_details(result)
            st.rerun()

    with col_back:
        if st.button("← Cockpit", key="portfolio_back_to_cockpit", use_container_width=True):
            go_to_cockpit()

    if "portfolio_mobile_view" not in st.session_state:
        st.session_state["portfolio_mobile_view"] = True

    with col_mobile:
        mobile_view = st.toggle("Vista mobile", value=True, key="portfolio_mobile_view")

    st.markdown('</div>', unsafe_allow_html=True)
    return bool(mobile_view)


def refresh_portfolio_quotes_action() -> None:
    clear_financial_data_cache()

    with st.spinner("Aggiornamento quotazioni in corso..."):
        result = refresh_portfolio_quotes(DATA_PATH)

    st.session_state["portfolio_last_auto_refresh_result"] = result
    st.session_state["portfolio_quotes_refreshed_on_load"] = True
    set_last_refresh_timestamp()

    if result["updated"] > 0:
        st.success(f"Quotazioni aggiornate: {result['updated']} su {result['total']}.")
    else:
        st.warning("Nessuna quotazione aggiornata. Mantengo i valori manuali presenti nel JSON.")

    render_refresh_details(result)
    st.rerun()


def render_add_form() -> None:
    with st.expander("➕ Aggiungi posizione", expanded=False):
        render_ticker_add_intro(
            title="➕ Aggiungi posizione",
            subtitle="Cerca per nome o ticker, scegli lo strumento corretto tra NASDAQ, NYSE e Milano, poi inserisci quantità e prezzo medio Fineco.",
        )

        selected_candidate = render_ticker_lookup_selector(key_prefix="portfolio_add")

        valuta = str(selected_candidate.get("currency") or "USD") if selected_candidate else "USD"
        mercato = str(selected_candidate.get("market") or "NASDAQ") if selected_candidate else "NASDAQ"

        info_cols = st.columns([1, 1])
        with info_cols[0]:
            st.text_input(
                "Valuta",
                value=valuta,
                disabled=True,
                key=f"portfolio_add_currency_readonly_{mercato}_{valuta}",
                help="La valuta viene calcolata dallo strumento selezionato e non va inserita manualmente.",
            )
        with info_cols[1]:
            st.text_input(
                "Mercato",
                value=mercato,
                disabled=True,
                key=f"portfolio_add_market_readonly_{mercato}_{valuta}",
                help="Il mercato viene calcolato dallo strumento selezionato.",
            )

        col4, col5 = st.columns([1, 1])
        with col4:
            quantita = st.number_input(
                "Quantità azioni",
                min_value=0,
                value=0,
                step=QTY_INPUT_STEP,
                format=QTY_INPUT_FORMAT,
                key="portfolio_add_qty",
            )
        with col5:
            prezzo_medio = st.number_input(
                "Prezzo medio per azione",
                min_value=0.0,
                value=0.0,
                step=PRICE_INPUT_STEP,
                format=PRICE_INPUT_FORMAT,
                key="portfolio_add_avg_price",
            )

        clean_qty = normalize_quantity(quantita)
        clean_avg_price = normalize_price(prezzo_medio)
        investimento = float(clean_qty) * float(clean_avg_price)
        conversion = convert_to_eur(investimento, valuta)

        preview_cols = st.columns(3)
        with preview_cols[0]:
            st.markdown(
                '<div class="portfolio-add-preview-card">'
                '<div class="portfolio-add-preview-label">Investimento di carico</div>'
                f'<div class="portfolio-add-preview-value">{fmt_eur(investimento)} {valuta}</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        with preview_cols[1]:
            eur_text = f"{fmt_eur(conversion.get('value'))} EUR" if conversion.get("ok") else "Cambio non disponibile"
            st.markdown(
                '<div class="portfolio-add-preview-card">'
                '<div class="portfolio-add-preview-label">Investimento in EUR</div>'
                f'<div class="portfolio-add-preview-value">{eur_text}</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        with preview_cols[2]:
            fx_text = (
                f"{fmt_num(conversion.get('rate'), 6)} · {conversion.get('source', '')}"
                if conversion.get("ok")
                else conversion.get("error", "Cambio non disponibile")
            )
            st.markdown(
                '<div class="portfolio-add-preview-card">'
                '<div class="portfolio-add-preview-label">Cambio usato</div>'
                f'<div class="portfolio-add-preview-value small">{fx_text}</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        if not conversion.get("ok") and valuta != "EUR":
            st.warning(
                f"Cambio {valuta}/EUR non disponibile da yfinance. "
                "Non aggiungo valori EUR stimati con fallback finti."
            )

        submitted = st.button("Aggiungi posizione", key="portfolio_add_smart_submit", use_container_width=True)
        if submitted:
            if not selected_candidate:
                st.warning("Cerca e seleziona un titolo valido.")
                return
            if clean_qty <= 0:
                st.warning("Quantità obbligatoria e maggiore di zero.")
                return
            if clean_avg_price <= 0:
                st.warning("Prezzo medio per azione obbligatorio e maggiore di zero.")
                return

            result = build_smart_position(
                ticker=selected_candidate.get("ticker", ""),
                mercato=selected_candidate.get("market", ""),
                valuta=selected_candidate.get("currency", ""),
                quantita=clean_qty,
                prezzo_medio=clean_avg_price,
                titolo=selected_candidate.get("name", ""),
                yf_symbol=selected_candidate.get("yf_symbol", ""),
                tv_symbol=selected_candidate.get("tv_symbol", ""),
            )
            add_position(DATA_PATH, result["position"])

            if not result.get("quote_ok"):
                quote_error = result.get("quote", {}).get("error", "prezzo non disponibile")
                st.warning(
                    f"Posizione aggiunta, ma quotazione non recuperata da yfinance ({quote_error}). "
                    "Uso temporaneamente il prezzo medio come prezzo mercato/precedente."
                )
            else:
                st.success("Posizione aggiunta con quotazione recuperata da yfinance.")

            st.rerun()

def _get_row_by_original_index(df, original_index: int):
    """Return row by original JSON index after display sorting."""
    if original_index not in df.index:
        return None
    return df.loc[original_index]


def _money(value: float, currency: str) -> str:
    suffix = f" {str(currency or '').upper()}" if currency else ""
    return f"{fmt_eur(value)}{suffix}"


def portfolio_display_symbol(row) -> str:
    """Return the best display symbol for a position.

    Prefer tv_symbol when present, e.g. MIL:1MSFT, otherwise fallback to
    mercato:ticker, e.g. NASDAQ:MSFT. This is generic and not hardcoded for
    Microsoft.
    """
    tv_symbol = str(row.get("tv_symbol", "") or "").strip().upper()
    if tv_symbol:
        return tv_symbol

    market = str(row.get("mercato", "") or "").strip().upper()
    ticker = str(row.get("ticker", "") or "").strip().upper()

    if market and ticker:
        return f"{market}:{ticker}"
    return ticker or market or "-"


def portfolio_display_market(row) -> str:
    """Return market part from tv_symbol if available, otherwise mercato."""
    display_symbol = portfolio_display_symbol(row)
    if ":" in display_symbol:
        return display_symbol.split(":", 1)[0].strip().upper()
    return str(row.get("mercato", "") or "").strip().upper()


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
    display_symbol = portfolio_display_symbol(row)

    fx_label = ""
    if currency != "EUR":
        fx_label = f" · FX {fmt_num(fx_eur, 4)}"
        if fx_eur == 1.0:
            fx_label += " ⚠️"

    header_html = (
        '<div class="portfolio-simulator-box">'
        '<div class="portfolio-simulator-kicker">Simulatore posizione</div>'
        f'<div class="portfolio-simulator-title">🧮 Simula acquisto aggiuntivo — {title}</div>'
        f'<div class="portfolio-simulator-subtitle">{display_symbol} · valuta {currency}{fx_label}</div>'
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
            step=PRICE_INPUT_STEP,
            format=PRICE_INPUT_FORMAT,
            key=f"portfolio_sim_buy_price_{simulation_index}",
        )

    with input_col_2:
        budget = st.number_input(
            f"Budget massimo opzionale ({currency})",
            min_value=0.0,
            value=0.0,
            step=100.0,
            format=PRICE_INPUT_FORMAT,
            key=f"portfolio_sim_budget_{simulation_index}",
            help="Se valorizzato, il simulatore calcola quante azioni puoi comprare con quel budget.",
        )

    budget_capacity = calculate_budget_capacity(budget, buy_price)
    suggested_budget_qty = calculate_suggested_quantity_from_budget(budget, buy_price)
    suggested_max = max(10, int(current_qty), int(suggested_budget_qty), 100)
    slider_max = min(max(suggested_max * 2, 100), 10000)

    slider_key = f"portfolio_sim_add_qty_{simulation_index}"
    budget_signature_key = f"portfolio_sim_budget_signature_{simulation_index}"
    budget_signature = (round(float(budget or 0.0), 2), round(float(buy_price or 0.0), 2))

    if slider_key not in st.session_state:
        st.session_state[slider_key] = 0

    if budget_signature != st.session_state.get(budget_signature_key):
        st.session_state[budget_signature_key] = budget_signature
        if float(budget or 0.0) > 0:
            st.session_state[slider_key] = min(int(slider_max), int(suggested_budget_qty))

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
        # Riga 1: dati anagrafici solo in lettura.
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Ticker", value=str(row.get("ticker", "")), disabled=True)
        with col2:
            st.text_input("Titolo", value=str(row.get("titolo", "")), disabled=True)
        with col3:
            st.text_input("Mercato TradingView", value=portfolio_display_market(row), disabled=True)

        # Riga 2: unici campi modificabili.
        col4, col5 = st.columns(2)
        with col4:
            quantita = st.number_input(
                "Quantità",
                min_value=0,
                value=normalize_quantity(row.get("quantita", 0.0)),
                step=QTY_INPUT_STEP,
                format=QTY_INPUT_FORMAT,
            )
        with col5:
            prezzo_medio = st.number_input(
                "P.zo medio carico",
                min_value=0.0,
                value=normalize_price(row.get("prezzo_medio", 0.0)),
                step=PRICE_INPUT_STEP,
                format=PRICE_INPUT_FORMAT,
            )

        # Riga 3: dati tecnici solo in lettura.
        col6, col7, col8 = st.columns(3)
        with col6:
            st.text_input("Valuta", value=str(row.get("valuta", "")), disabled=True)
        with col7:
            st.text_input("Simbolo yfinance", value=str(row.get("yf_symbol", "")), disabled=True)
        with col8:
            st.text_input("Simbolo TradingView", value=str(row.get("tv_symbol", "")), disabled=True)

        col_save, col_cancel = st.columns([1, 5])

        with col_save:
            submitted = st.form_submit_button("Salva")

        with col_cancel:
            cancelled = st.form_submit_button("Annulla")

        if submitted:
            update_position(
                DATA_PATH,
                edit_index,
                {
                    "quantita": normalize_quantity(quantita),
                    "prezzo_medio": normalize_price(prezzo_medio),
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
    st.warning(f"Confermi l'eliminazione di {row['titolo']} ({portfolio_display_symbol(row)})?")

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


def render_inline_position_panel(df, original_index: int) -> None:
    """Render simulator/edit/delete panel immediately below the selected row/card."""
    active_indexes = {
        st.session_state.get("portfolio_simulation_index"),
        st.session_state.get("portfolio_edit_index"),
        st.session_state.get("portfolio_delete_index"),
    }

    if original_index not in active_indexes:
        return

    if original_index not in df.index:
        return

    st.markdown('<div class="portfolio-inline-panel-spacer"></div>', unsafe_allow_html=True)
    row_df = df.loc[[original_index]]

    render_buy_simulator(row_df)
    render_edit_form(row_df)
    render_delete_confirmation(row_df)


def render_portfolio_rows(df) -> None:
    render_portfolio_table_header()

    for idx, row in df.iterrows():
        action_col = render_position_values(row)

        with action_col:
            st.markdown('<div class="portfolio-action-spacer"></div>', unsafe_allow_html=True)
            action_cols = st.columns([1, 1, 1, 1, 1], gap="small")

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
                if st.button("🎯", key=f"portfolio_target_{idx}", help="Apri Target Analisti interno", use_container_width=True):
                    open_portfolio_target_page(row)

            with action_cols[2]:
                if st.button("🧮", key=f"portfolio_sim_{idx}", help="Simula acquisto aggiuntivo"):
                    st.session_state["portfolio_simulation_index"] = idx
                    st.session_state["portfolio_edit_index"] = None
                    st.session_state["portfolio_delete_index"] = None
                    st.rerun()

            with action_cols[3]:
                if st.button("✏️", key=f"portfolio_edit_{idx}", help="Modifica posizione"):
                    st.session_state["portfolio_edit_index"] = idx
                    st.session_state["portfolio_delete_index"] = None
                    st.session_state["portfolio_simulation_index"] = None
                    st.rerun()

            with action_cols[4]:
                if st.button("🗑️", key=f"portfolio_delete_{idx}", help="Elimina posizione"):
                    st.session_state["portfolio_delete_index"] = idx
                    st.session_state["portfolio_edit_index"] = None
                    st.session_state["portfolio_simulation_index"] = None
                    st.rerun()

        render_inline_position_panel(df, idx)
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

    # Refresh automatico browser disattivato: evita reload forzati che possono
    # interrompere la sessione Streamlit/login. I dati si aggiornano con il
    # pulsante 🔄 dell'header, con il refresh manuale browser o al cambio pagina.

    mobile_view = render_standard_page_header(
        title="💼 Portafoglio",
        subtitle="Gestione posizioni, valori di mercato e grafico TradingView.",
        toggle_label="📱 Vista mobile",
        toggle_key="portfolio_mobile_view",
        toggle_default=True,
        refresh_key="portfolio_header_refresh",
        back_key="portfolio_header_back",
        refresh_callback=refresh_portfolio_quotes_action,
    )

    render_add_form()

    auto_refresh_quotes_on_page_open()
    render_auto_refresh_status()

    df = load_portfolio(DATA_PATH)
    df = enrich_portfolio_df(df)

    render_persistence_note()

    totals = portfolio_totals(df)
    if mobile_view:
        render_mobile_portfolio_summary(totals)
    else:
        render_portfolio_summary(totals)

    if df.empty:
        st.info("Il portafoglio è vuoto. Aggiungi la prima posizione.")
        return

    df_display = sort_portfolio_for_display(df)

    if mobile_view:
        render_mobile_portfolio_rows(
            df_display,
            portfolio_tradingview_url,
            inline_renderer=render_inline_position_panel,
            target_renderer=open_portfolio_target_page,
        )
    else:
        render_portfolio_rows(df_display)


if __name__ == "__main__":
    main()
