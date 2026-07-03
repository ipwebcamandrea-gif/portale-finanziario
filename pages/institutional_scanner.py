import html
import math
import re
from pathlib import Path

import streamlit as st

from components.standard_header import render_standard_page_header
from utils.institutional_scanner import fmt_price, fmt_pct, safe_float, scan_summary, scan_symbols
from utils.target_data import fetch_yfinance_targets
from utils.target_symbol_resolver import tradingview_forecast_url
from utils.symbols import normalize_tradingview_symbol, strip_exchange_prefix
from utils.watchlist_storage import carica_watchlists_da_json

PAGE_TITLE = "BUY ZONE FINDER"
SESSION_SCAN_REQUEST_KEY = "buy_zone_finder_force_refresh"

st.set_page_config(page_title=PAGE_TITLE, layout="wide")


def escape(value, quote: bool = False) -> str:
    return html.escape(str(value if value is not None else ""), quote=quote)


def load_page_css() -> None:
    css_path = Path("css/institutional_scanner.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


load_page_css()


def refresh_scan() -> None:
    st.cache_data.clear()
    st.session_state[SESSION_SCAN_REQUEST_KEY] = True


def load_buy_zone_watchlists() -> dict:
    try:
        data = carica_watchlists_da_json()
    except Exception:
        data = {"active_watchlist": "Default", "watchlists": {"Default": []}}

    watchlists = data.get("watchlists") if isinstance(data, dict) else {}
    if not isinstance(watchlists, dict) or not watchlists:
        watchlists = {"Default": []}

    active = data.get("active_watchlist") if isinstance(data, dict) else None
    if active not in watchlists:
        active = list(watchlists.keys())[0]

    return {"active_watchlist": active, "watchlists": watchlists}


def render_watchlist_selector_panel(data: dict) -> tuple[str, tuple[str, ...]]:
    watchlists = data.get("watchlists", {})
    names = list(watchlists.keys()) or ["Default"]
    active = data.get("active_watchlist") if data.get("active_watchlist") in names else names[0]

    if "buy_zone_selected_watchlist" not in st.session_state or st.session_state.get("buy_zone_selected_watchlist") not in names:
        st.session_state["buy_zone_selected_watchlist"] = active

    st.markdown(
        '<div class="buyzone-watchlist-panel">'
        '<div class="buyzone-watchlist-title">Watchlist TradingView</div>'
        '<div class="buyzone-watchlist-subtitle">Scegli quale watchlist analizzare. BUY ZONE FINDER calcola i segnali solo sui ticker contenuti nella lista selezionata.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    select_col, count_col = st.columns([3.4, 1.0], vertical_alignment="bottom")
    with select_col:
        selected = st.selectbox(
            "Watchlist selezionata",
            options=names,
            index=names.index(st.session_state["buy_zone_selected_watchlist"]),
            key="buy_zone_watchlist_selector",
            help="Elenco caricato dalle Watchlist TradingView salvate per l'utente corrente.",
        )
    st.session_state["buy_zone_selected_watchlist"] = selected

    symbols = tuple(str(s).strip().upper() for s in watchlists.get(selected, []) if str(s).strip())

    with count_col:
        st.markdown(
            f'<div class="buyzone-watchlist-count"><strong>{len(symbols)}</strong><span>ticker</span></div>',
            unsafe_allow_html=True,
        )

    preview = list(symbols[:8])
    chips = "".join(f"<span>{escape(sym)}</span>" for sym in preview)
    if len(symbols) > len(preview):
        chips += f'<span class="more">+{len(symbols) - len(preview)}</span>'

    if chips:
        st.markdown(f'<div class="buyzone-watchlist-chips">{chips}</div>', unsafe_allow_html=True)
    else:
        st.warning("La watchlist selezionata non contiene ticker.")

    return selected, symbols


def filter_records_by_confluence(records: list[dict], selected_filter: str) -> list[dict]:
    if selected_filter == "Tutte":
        return records
    try:
        wanted = int(str(selected_filter).split("/", 1)[0])
    except Exception:
        return records
    return [r for r in records if int(r.get("confluence_count") or 0) == wanted]


def render_condition_filter(records: list[dict]) -> str:
    counts = {i: 0 for i in range(4)}
    for r in records:
        c = int(r.get("confluence_count") or 0)
        if c in counts:
            counts[c] += 1

    options = ["3/3 Buy", "2/3 Watch", "1/3 Early", "0/3", "Tutte"]
    labels = {
        "3/3 Buy": f"3/3 Buy ({counts[3]})",
        "2/3 Watch": f"2/3 Watch ({counts[2]})",
        "1/3 Early": f"1/3 Early ({counts[1]})",
        "0/3": f"0/3 ({counts[0]})",
        "Tutte": f"Tutte ({len(records)})",
    }

    if "buy_zone_condition_filter" not in st.session_state or st.session_state.get("buy_zone_condition_filter") not in options:
        st.session_state["buy_zone_condition_filter"] = "2/3 Watch"

    st.markdown(
        '<div class="buyzone-filter-panel">'
        '<div class="buyzone-filter-title">Filtro condizioni attive</div>'
        '<div class="buyzone-filter-subtitle">Default: mostra solo Watch tecnico 2/3. Cambiare filtro non riesegue lo scanner.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    selected = st.radio(
        "Filtro condizioni attive",
        options=options,
        format_func=lambda x: labels.get(x, x),
        index=options.index(st.session_state["buy_zone_condition_filter"]),
        horizontal=True,
        key="buy_zone_condition_filter_radio",
        label_visibility="collapsed",
    )
    st.session_state["buy_zone_condition_filter"] = selected
    return selected


@st.cache_data(ttl=15 * 60, show_spinner=False)
def load_cached_scan(symbols: tuple[str, ...]) -> list[dict]:
    return run_full_scan(symbols)


def run_full_scan(symbols: tuple[str, ...]) -> list[dict]:
    bar = st.progress(0, text="Preparazione dati tecnici weekly...")

    def cb(i: int, total: int, item: dict) -> None:
        label = item.get("ticker") or item.get("yahoo") or ""
        bar.progress((i - 1) / max(total, 1), text=f"Calcolo SMA200W/LinReg W {i}/{total}: {label}")

    records = scan_symbols(symbols=symbols, progress_callback=cb)
    bar.progress(1.0, text="Scanner tecnico completato")
    bar.empty()
    return records


def vclass(value) -> str:
    v = safe_float(value)
    if v is None:
        return "neutral"
    return "positive" if v >= 0 else "negative"


def yesno(active: bool) -> str:
    return "ATTIVO" if active else "NO"


def condition_metric(title: str, pct: str, value: str, active: bool, value_class: str = "neutral") -> str:
    state_class = "active" if active else "inactive"
    return (
        f'<div class="condition-metric {state_class}">'
        f'<span>{escape(title)}</span>'
        f'<strong class="{escape(value_class)}">{escape(pct)}</strong>'
        f'<small>{escape(value)}</small>'
        f'<em>{yesno(active)}</em>'
        '</div>'
    )


def reason_block(record: dict) -> str:
    rows = []
    rows.append((bool(record.get("below_sma200w")), "Sotto SMA200W"))
    rows.append((bool(record.get("near_hist_min_w")), "Min W Storico"))
    rows.append((bool(record.get("near_linreg_lower")), "LinReg Lower" if bool(record.get("near_linreg_lower")) else "No LinReg Lower"))
    html_rows = []
    for ok, label in rows:
        icon = "✓" if ok else "×"
        cls = "ok" if ok else "ko"
        html_rows.append(f'<div class="reason-line {cls}"><b>{icon}</b><span>{escape(label)}</span></div>')
    return "".join(html_rows)


def line_top(value, low, high) -> float:
    v = safe_float(value)
    lo = safe_float(low)
    hi = safe_float(high)
    if v is None or lo is None or hi is None or hi <= lo:
        return 50.0
    # Mantiene le label LinReg dentro al box anche nelle card strette.
    return max(13.0, min(87.0, 87.0 - ((v - lo) / (hi - lo)) * 74.0))


def linreg_section(record: dict, currency: str) -> str:
    lower = safe_float(record.get("linreg_lower_w"))
    mid = safe_float(record.get("linreg_mid_w"))
    upper = safe_float(record.get("linreg_upper_w"))
    price = safe_float(record.get("last_price"))
    if lower is None or mid is None or upper is None or price is None:
        return '<div class="linreg-box"><h4>LinReg W</h4><div class="linreg-empty">Dati LinReg non disponibili.</div></div>'

    scale_min = min(lower, price)
    scale_max = max(upper, price)
    upper_top = line_top(upper, scale_min, scale_max)
    mid_top = line_top(mid, scale_min, scale_max)
    lower_top = line_top(lower, scale_min, scale_max)
    price_top = line_top(price, scale_min, scale_max)

    return (
        '<div class="linreg-box">'
        '<h4>LinReg W</h4>'
        '<div class="linreg-subtitle">LinReg 100 close 2 2 - 100 settimane</div>'
        '<div class="linreg-visual">'
        f'<div class="linreg-level upper" style="top:{upper_top}%"><span>UPPER</span><b>{escape(fmt_price(upper, currency))}</b></div>'
        f'<div class="linreg-level mid" style="top:{mid_top}%"><span>MID</span><b>{escape(fmt_price(mid, currency))}</b></div>'
        f'<div class="linreg-level lower" style="top:{lower_top}%"><span>LOWER</span><b>{escape(fmt_price(lower, currency))}</b></div>'
        f'<div class="linreg-price-line" style="top:{price_top}%"><span>Prezzo {escape(fmt_price(price, currency))}</span></div>'
        '</div>'
        '</div>'
    )


def technical_details(record: dict, currency: str) -> str:
    items = [
        ("SMA200W", fmt_price(record.get("sma200w"), currency)),
        ("Hist Min W", fmt_pct(record.get("hist_min_w_pct"), 1)),
        ("MinW Low", fmt_price(record.get("hist_min_w_low"), currency)),
        ("Eq Min W", fmt_price(record.get("hist_min_equivalent"), currency)),
        ("Hist Max W", fmt_pct(record.get("hist_max_w_pct"), 1)),
        ("LinReg Lower", fmt_price(record.get("linreg_lower_w"), currency)),
        ("LinReg Mid", fmt_price(record.get("linreg_mid_w"), currency)),
        ("LinReg Upper", fmt_price(record.get("linreg_upper_w"), currency)),
    ]
    return '<div class="technical-details-grid">' + ''.join(f'<div><span>{escape(k)}</span><strong>{escape(v)}</strong></div>' for k, v in items) + '</div>'


def _underlying_forecast_identity(record: dict) -> dict:
    """Return the symbol identity to use for analyst forecasts.

    Technical cards can be based on local listings such as 1MSFT.MI.
    Analyst forecasts usually exist only for the underlying US symbol, so
    1MSFT.MI must use MSFT for yfinance and TradingView Forecast.
    """
    yf = str(record.get("yahoo") or record.get("ticker") or "").strip().upper()
    ticker = str(record.get("ticker") or yf or "").strip().upper()
    tv = str(record.get("tv") or "").strip().upper()

    underlying = None
    if yf.startswith("1") and yf.endswith(".MI") and len(yf) > 4:
        core = yf[1:-3].strip().upper()
        if core:
            underlying = core
    elif ticker.startswith("1") and ticker.endswith(".MI") and len(ticker) > 4:
        core = ticker[1:-3].strip().upper()
        if core:
            underlying = core

    if underlying:
        tv_underlying = normalize_tradingview_symbol(underlying)
        return {
            "yf_symbol": underlying,
            "ticker": strip_exchange_prefix(tv_underlying) or underlying,
            "tv_symbol": tv_underlying,
            "market": tv_underlying.split(":", 1)[0] if ":" in tv_underlying else "",
            "display": strip_exchange_prefix(tv_underlying) or underlying,
            "note": f"Forecast sul sottostante {strip_exchange_prefix(tv_underlying) or underlying}",
        }

    market = tv.split(":", 1)[0] if ":" in tv else ""
    return {
        "yf_symbol": yf,
        "ticker": ticker,
        "tv_symbol": tv,
        "market": market,
        "display": ticker,
        "note": "",
    }

def _forecast_key(record: dict) -> str:
    ident = _underlying_forecast_identity(record)
    raw = str(ident.get("yf_symbol") or record.get("yahoo") or record.get("ticker") or "").strip().upper()
    return "buy_zone_forecast_" + re.sub(r"[^A-Z0-9_]+", "_", raw)


def _forecast_url(record: dict) -> str:
    ident = _underlying_forecast_identity(record)
    return tradingview_forecast_url(
        ident.get("tv_symbol") or "",
        yf_symbol=ident.get("yf_symbol") or "",
        market=ident.get("market") or "",
        ticker=ident.get("ticker") or "",
    )


def forecast_bar_top(value, low, high) -> float:
    v = safe_float(value)
    lo = safe_float(low)
    hi = safe_float(high)
    if v is None or lo is None or hi is None or hi <= lo:
        return 50.0
    return max(8.0, min(92.0, 92.0 - ((v - lo) / (hi - lo)) * 84.0))


def signed_delta_value(target, current) -> str:
    t = safe_float(target)
    c = safe_float(current)
    if t is None or c is None:
        return "N/D"
    sign = "+" if (t - c) >= 0 else ""
    return f"{sign}{t-c:.2f}"


def forecast_history_path(current_top: float) -> str:
    return (
        "M0,68 L7,58 L13,62 L20,49 L27,42 L33,50 L40,45 "
        "L47,48 L54,43 L61,36 L68,49 L75,45 L82,58 L89,66 "
        f"L100,{current_top:.2f}"
    )


def forecast_chart_html(record: dict, data: dict) -> str:
    currency = str(data.get("currency") or record.get("currency") or "").upper()
    current = safe_float(data.get("current_price") or record.get("last_price"))
    low = safe_float(data.get("target_low"))
    mean = safe_float(data.get("target_mean"))
    high = safe_float(data.get("target_high"))
    analysts = data.get("analyst_count") or "N/D"
    if current is None or low is None or mean is None or high is None:
        return '<div class="forecast-empty">Target incompleti per questo titolo.</div>'
    pct_avg = ((mean - current) / current * 100) if current else None
    pct_max = ((high - current) / current * 100) if current else None
    pct_min = ((low - current) / current * 100) if current else None
    scale_low = min(low, current)
    scale_high = max(high, mean, current)
    max_top = forecast_bar_top(high, scale_low, scale_high)
    avg_top = forecast_bar_top(mean, scale_low, scale_high)
    cur_top = forecast_bar_top(current, scale_low, scale_high)
    min_top = forecast_bar_top(low, scale_low, scale_high)
    min_label_top = min(92.0, min_top + 8.0)
    current_label_top = min(92.0, cur_top + 16.0)

    # Convert plot-area percentages to chart-area percentages.
    # SVG history/cone use an inner plotting area; marker/labels are in the outer chart.
    def chart_area_top(pct: float) -> float:
        return max(2.0, min(96.0, 8.6 + (float(pct) * 0.786)))

    def spread_label_tops(label_items: list[tuple[str, float]]) -> dict[str, float]:
        """Avoid overlapping right-side forecast labels.

        Labels such as Current and Min can land on nearly the same vertical
        coordinate when current price is close to the low target. This small
        deterministic layout pass preserves the natural order and guarantees
        a minimum distance between labels inside the chart.
        """
        min_gap = 10.5
        top_bound = 8.0
        bottom_bound = 90.0
        ordered = sorted([(name, max(top_bound, min(bottom_bound, float(top)))) for name, top in label_items], key=lambda item: item[1])
        for idx in range(1, len(ordered)):
            prev_name, prev_top = ordered[idx - 1]
            name, top = ordered[idx]
            if top - prev_top < min_gap:
                ordered[idx] = (name, prev_top + min_gap)
        overflow = ordered[-1][1] - bottom_bound if ordered else 0
        if overflow > 0:
            ordered = [(name, top - overflow) for name, top in ordered]
            for idx in range(len(ordered) - 2, -1, -1):
                next_name, next_top = ordered[idx + 1]
                name, top = ordered[idx]
                if next_top - top < min_gap:
                    ordered[idx] = (name, next_top - min_gap)
        ordered = [(name, max(top_bound, min(bottom_bound, top))) for name, top in ordered]
        return dict(ordered)

    raw_label_tops = {
        "max": chart_area_top(max_top),
        "avg": chart_area_top(avg_top),
        "current": chart_area_top(current_label_top),
        "min": chart_area_top(min_label_top),
    }
    adjusted_label_tops = spread_label_tops(list(raw_label_tops.items()))
    max_chart_top = adjusted_label_tops["max"]
    avg_chart_top = adjusted_label_tops["avg"]
    current_label_chart_top = adjusted_label_tops["current"]
    min_chart_top = adjusted_label_tops["min"]
    cur_chart_top = chart_area_top(cur_top)
    history_path = escape(forecast_history_path(cur_top), quote=True)
    return (
        '<div class="forecast-loaded">'
        '<div class="forecast-head"><div><div class="forecast-eyebrow">Price target</div>'
        f'<div class="forecast-main"><strong>{mean:.2f}</strong><span>{escape(currency)}</span><em>{escape(signed_delta_value(mean,current))}</em><em>{escape(fmt_pct(pct_avg,2))}</em></div></div>'
        f'<p>{escape(str(analysts))} analisti · Max {high:.2f} · Min {low:.2f}</p></div>'
        '<div class="forecast-chart">'
        f'<svg class="forecast-history" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="{history_path}"/></svg>'
        f'<div class="forecast-anchor" style="top:{cur_chart_top}%"></div>'
        f'<div class="forecast-cone forecast-green" style="clip-path:polygon(0% {cur_top}%,100% {max_top}%,100% {avg_top}%)"></div>'
        f'<div class="forecast-cone forecast-red" style="clip-path:polygon(0% {cur_top}%,100% {avg_top}%,100% {min_top}%)"></div>'
        f'<div class="forecast-line current" style="top:{cur_chart_top}%"></div>'
        f'<div class="forecast-current-solid" style="top:{cur_chart_top}%"></div>'
        f'<div class="forecast-label max" style="top:{max_chart_top}%"><b>Max {escape(fmt_pct(pct_max,2))}</b><strong>{high:.2f}</strong></div>'
        f'<div class="forecast-label avg" style="top:{avg_chart_top}%"><b>Avg {escape(fmt_pct(pct_avg,2))}</b><strong>{mean:.2f}</strong></div>'
        f'<div class="forecast-label min" style="top:{min_chart_top}%"><b>Min {escape(fmt_pct(pct_min,2))}</b><strong>{low:.2f}</strong></div>'
        f'<div class="forecast-label current-l" style="top:{current_label_chart_top}%"><b>Current</b><strong>{current:.2f}</strong></div>'
        '<div class="forecast-date forecast-date-left">2026</div><div class="forecast-date forecast-date-mid">Jul</div><div class="forecast-date forecast-date-right">2027</div>'
        '</div></div>'
    )


def open_target_page_from_record(record: dict) -> None:
    ident = _underlying_forecast_identity(record)
    st.session_state["target_selected"] = {
        "yf_symbol": str(ident.get("yf_symbol") or "").strip().upper(),
        "ticker": str(ident.get("ticker") or "").strip().upper(),
        "tv_symbol": str(ident.get("tv_symbol") or "").strip().upper(),
        "name": str(record.get("name") or "").strip(),
        "market": str(ident.get("market") or "").strip().upper(),
        "currency": str(record.get("currency") or "").strip().upper(),
        "source": "direct",
    }
    st.session_state["target_source"] = "direct"
    st.switch_page("pages/target_analisti.py")


def render_forecast_on_demand(record: dict, rank: int, column_index: int, row_index: int) -> None:
    ident = _underlying_forecast_identity(record)
    key = _forecast_key(record)
    display = ident.get("display") or record.get("ticker") or "-"
    title = f"Price Target Forecast · {display}"
    with st.expander(title, expanded=False):
        url = _forecast_url(record)
        note = ident.get("note") or ""
        if note:
            st.caption(note)
        data = st.session_state.get(key)
        status = st.session_state.get(key + "_status", "idle")
        if isinstance(data, dict) and data.get("ok"):
            st.markdown(forecast_chart_html(record, data), unsafe_allow_html=True)
        else:
            if status == "error":
                err = st.session_state.get(key + "_error", "Dati forecast temporaneamente non disponibili.")
                st.markdown(f'<div class="forecast-empty">{escape(str(err))}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="forecast-empty">Dati forecast non ancora scaricati per questo titolo.</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1.45, 1.05, 1.15])
        safe_key = re.sub(r"[^A-Z0-9_]+", "_", str(ident.get("yf_symbol") or record.get("yahoo") or record.get("ticker") or rank).upper())
        with c1:
            if st.button("Scarica dati forecast", key=f"download_forecast_{row_index}_{column_index}_{safe_key}"):
                yf_symbol = str(ident.get("yf_symbol") or record.get("yahoo") or "").strip().upper()
                tv_symbol = str(ident.get("tv_symbol") or record.get("tv") or "").strip().upper()
                ticker = str(ident.get("ticker") or record.get("ticker") or "").strip().upper()
                market = str(ident.get("market") or (tv_symbol.split(":", 1)[0] if ":" in tv_symbol else "")).strip().upper()
                with st.spinner(f"Scarico forecast {ticker or yf_symbol}..."):
                    result = fetch_yfinance_targets(
                        yf_symbol,
                        ticker=ticker,
                        market=market,
                        currency=str(record.get("currency") or ""),
                        tv_symbol=tv_symbol,
                    )
                if result.get("ok"):
                    st.session_state[key] = result
                    st.session_state[key + "_status"] = "ok"
                    st.session_state.pop(key + "_error", None)
                else:
                    st.session_state[key + "_status"] = "error"
                    st.session_state[key + "_error"] = result.get("error") or "Dati forecast temporaneamente non disponibili. Riprova tra qualche minuto."
                st.rerun()
        with c2:
            st.link_button("Apri Forecast", url, use_container_width=True)
        with c3:
            if st.button("Target Analisti", key=f"target_page_{row_index}_{column_index}_{safe_key}", use_container_width=True):
                open_target_page_from_record(record)


def card(record: dict, rank: int) -> str:
    currency = str(record.get("currency") or "").upper()
    ticker = str(record.get("ticker") or "")
    name = str(record.get("name") or "")
    label = str(record.get("technical_label") or "Monitor tecnico")
    count = int(record.get("confluence_count") or 0)
    tv_url = escape(str(record.get("tradingview_url") or "#"), quote=True)
    card_class = "is-buy" if count == 3 else "is-watch" if count == 2 else "is-monitor"
    badge_class = "badge-buy" if count == 3 else "badge-watch" if count == 2 else "badge-monitor"

    html = f'<div class="redesign-card {card_class}">'
    html += f'<div class="card-top"><div class="rank">#{rank}</div><div class="identity"><div class="ticker-row"><strong>{escape(ticker)}</strong></div><div class="company-name">{escape(name)}</div></div><div class="status-badge {badge_class}">{escape(label)} <span>{count}/3</span></div></div>'
    html += f'<div class="decision-row"><div class="price-main"><span>Prezzo</span><strong>{escape(fmt_price(record.get("last_price"), currency))}</strong><small class="{vclass(record.get("daily_change_pct"))}">Daily {escape(fmt_pct(record.get("daily_change_pct"), 2))}</small></div><div class="decision-text"><span>Motivo principale</span>{reason_block(record)}</div></div>'
    html += '<div class="condition-metrics-row">'
    html += condition_metric("Distanza SMA200W", fmt_pct(record.get("dist_pct"), 2), fmt_price(record.get("sma200w"), currency), bool(record.get("below_sma200w")), vclass(record.get("dist_pct")))
    html += condition_metric("Scarto Min W Hist", fmt_pct(record.get("gap_points"), 1), fmt_price(record.get("hist_min_equivalent"), currency), bool(record.get("near_hist_min_w")), "neutral")
    html += condition_metric("LinReg Lower", fmt_pct(record.get("linreg_dist_lower_pct"), 2), fmt_price(record.get("linreg_lower_w"), currency), bool(record.get("near_linreg_lower")), vclass(record.get("linreg_dist_lower_pct")))
    html += '</div>'
    html += linreg_section(record, currency)
    html += '<details class="details-expander"><summary>Dettagli SMA200W / Storico</summary>' + technical_details(record, currency) + '</details>'
    html += f'<div class="card-actions"><a href="{tv_url}" target="_blank" rel="noopener noreferrer">Apri TradingView</a></div></div>'
    return html


render_standard_page_header(
    title="BUY ZONE FINDER",
    subtitle="Scanner tecnico weekly: SMA200W, Min W storico, LinReg Lower W e Forecast on demand.",
    toggle_label="Vista compatta",
    toggle_key="linreg_compact_mode",
    toggle_default=True,
    refresh_key="linreg_header_refresh",
    back_key="linreg_header_back",
    refresh_callback=refresh_scan,
)

watchlist_data = load_buy_zone_watchlists()
selected_watchlist, selected_symbols = render_watchlist_selector_panel(watchlist_data)

if selected_symbols:
    records = run_full_scan(selected_symbols) if bool(st.session_state.pop(SESSION_SCAN_REQUEST_KEY, False)) else load_cached_scan(selected_symbols)
else:
    st.session_state.pop(SESSION_SCAN_REQUEST_KEY, None)
    records = []

summary = scan_summary(records)
cols = st.columns(4)
summary_items = [
    ("Titoli", str(summary.get("count", 0)), selected_watchlist),
    ("Buy Zone", str(summary.get("buy_count", 0)), "3/3 condizioni"),
    ("Watch", str(summary.get("watch_count", 0)), "2/3 condizioni"),
    ("Sotto SMA200W +\nVicino al Min W\nStorico", str(summary.get("orange_count", 0)), "SMA200W + Min W"),
]
for col, (summary_label, summary_value, summary_note) in zip(cols, summary_items):
    with col:
        label_html = escape(summary_label).replace("\n", "<br>")
        st.markdown(
            f'<div class="summary-card"><div class="summary-label">{label_html}</div><div class="summary-value">{escape(summary_value)}</div><div class="summary-note">{escape(summary_note)}</div></div>',
            unsafe_allow_html=True,
        )

st.caption(f"Ultimo aggiornamento: {summary.get('last_update', '-')}. Cache 15 minuti. Forecast scaricato solo su richiesta della singola card.")
selected_condition_filter = render_condition_filter(records) if records else "2/3 Watch"
filtered_records = filter_records_by_confluence(records, selected_condition_filter)
st.markdown(
    f'<div class="section-title">Scanner tecnico <span class="section-watchlist-name">· {escape(selected_watchlist)} · {escape(selected_condition_filter)}</span></div>',
    unsafe_allow_html=True,
)

if filtered_records:
    for row_index, start in enumerate(range(0, len(filtered_records), 3), 1):
        row_records = filtered_records[start:start + 3]
        row_cols = st.columns(3)
        for col_index, (col, record) in enumerate(zip(row_cols, row_records), 1):
            rank = start + col_index
            with col:
                wrap_key = re.sub(r"[^A-Za-z0-9_]+", "_", str(record.get("yahoo") or record.get("ticker") or rank))
                with st.container(key=f"buyzone_forecast_wrap_{row_index}_{col_index}_{wrap_key}"):
                    st.markdown(card(record, rank), unsafe_allow_html=True)
                    render_forecast_on_demand(record, rank, col_index, row_index)
        st.markdown('<div class="buyzone-card-spacer"></div>', unsafe_allow_html=True)
elif records:
    st.info("Nessuna card corrisponde al filtro selezionato.")
else:
    st.warning("Nessun dato disponibile per la watchlist selezionata.")

errors = [record for record in records if str(record.get("error") or "").strip()]
if errors:
    with st.expander(f"Titoli con dati tecnici incompleti ({len(errors)})", expanded=False):
        for record in errors:
            st.write(f"{record.get('ticker', '-')}: {record.get('error')}")
