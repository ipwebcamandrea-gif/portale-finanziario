from __future__ import annotations
from html import escape
from pathlib import Path
import streamlit as st
import re
from components.standard_header import render_standard_page_header
from utils.app_branding import render_app_icon_meta
from utils.auth import require_login
from utils.institutional_scanner import fmt_price, fmt_pct, safe_float, scan_summary, scan_symbols
from utils.watchlist_storage import carica_watchlists_da_json
from utils.target_data import fetch_yfinance_targets
from utils.target_symbol_resolver import tradingview_forecast_url

require_login()
ROOT_DIR = Path(__file__).resolve().parent.parent
GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
PAGE_CSS = ROOT_DIR / "css" / "institutional_scanner.css"
SESSION_SCAN_REQUEST_KEY = "technical_linreg_scan_requested"

def local_css(file_path: Path) -> None:
    if file_path.exists():
        st.markdown(f"<style>{file_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

local_css(GLOBAL_CSS); local_css(PAGE_CSS); render_app_icon_meta()

def run_full_scan(symbols: tuple[str, ...]) -> list[dict]:
    bar = st.progress(0, text="Preparazione dati tecnici weekly...")
    def cb(i: int, total: int, item: dict) -> None:
        label = item.get('ticker') or item.get('yahoo') or ''
        bar.progress((i - 1) / max(total, 1), text=f"Calcolo SMA200W/LinReg W {i}/{total}: {label}")
    records = scan_symbols(symbols=symbols, progress_callback=cb)
    bar.progress(1.0, text="Scanner tecnico completato")
    bar.empty()
    return records

def refresh_scan() -> None:
    st.cache_data.clear(); st.session_state[SESSION_SCAN_REQUEST_KEY] = True; st.rerun()

@st.cache_data(ttl=15 * 60, show_spinner=False)
def load_cached_scan(symbols: tuple[str, ...]) -> list[dict]:
    return run_full_scan(symbols)

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
    st.markdown('<div class="buyzone-watchlist-panel"><div class="buyzone-watchlist-title">Watchlist TradingView</div><div class="buyzone-watchlist-subtitle">Scegli quale watchlist analizzare. BUY ZONE FINDER calcola i segnali solo sui ticker contenuti nella lista selezionata.</div></div>', unsafe_allow_html=True)
    select_col, count_col = st.columns([3.4, 1.0], vertical_alignment="bottom")
    with select_col:
        selected = st.selectbox("Watchlist selezionata", options=names, index=names.index(st.session_state["buy_zone_selected_watchlist"]), key="buy_zone_watchlist_selector", help="Elenco caricato dalle Watchlist TradingView salvate per l'utente corrente.")
    st.session_state["buy_zone_selected_watchlist"] = selected
    symbols = tuple(str(s).strip().upper() for s in watchlists.get(selected, []) if str(s).strip())
    with count_col:
        st.markdown(f'<div class="buyzone-watchlist-count"><strong>{len(symbols)}</strong><span>ticker</span></div>', unsafe_allow_html=True)
    preview = list(symbols[:8])
    chips = ''.join(f'<span>{escape(sym)}</span>' for sym in preview)
    if len(symbols) > len(preview):
        chips += f'<span class="more">+{len(symbols)-len(preview)}</span>'
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
    st.markdown('<div class="buyzone-filter-panel"><div class="buyzone-filter-title">Filtro condizioni attive</div><div class="buyzone-filter-subtitle">Default: mostra solo Watch tecnico 2/3. Cambiare filtro non riesegue lo scanner.</div></div>', unsafe_allow_html=True)
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

def _forecast_key(record: dict) -> str:
    raw = str(record.get("yahoo") or record.get("ticker") or "").strip().upper()
    return "buy_zone_forecast_" + re.sub(r"[^A-Z0-9_]+", "_", raw)

def _forecast_url(record: dict) -> str:
    tv = str(record.get("tv") or "").strip().upper()
    yf = str(record.get("yahoo") or "").strip().upper()
    ticker = str(record.get("ticker") or "").strip().upper()
    market = tv.split(":", 1)[0] if ":" in tv else ""
    return tradingview_forecast_url(tv, yf_symbol=yf, market=market, ticker=ticker)

def vclass(value) -> str:
    x = safe_float(value)
    if x is None: return "neutral"
    if x > 0: return "positive"
    if x < 0: return "negative"
    return "neutral"

def detail_item(label: str, value: str, css: str = "") -> str:
    return f'<div class="detail-item"><span class="detail-label">{escape(label)}</span><span class="detail-value {css}">{escape(value)}</span></div>'

def condition_metric(label: str, value: str, subvalue: str, active: bool, value_css: str = "") -> str:
    state = "ATTIVO" if active else "NO"
    css = "condition-metric-on" if active else "condition-metric-off"
    return f'<div class="condition-metric {css}"><span class="condition-metric-label">{escape(label)}</span><strong class="condition-metric-value {value_css}">{escape(value)}</strong><span class="condition-metric-subvalue">{escape(subvalue)}</span><span class="condition-metric-state">{state}</span></div>'

def reason_line(active: bool, text: str) -> str:
    css = "reason-ok" if active else "reason-ko"; mark = "✓" if active else "✕"
    return f'<div class="reason-line {css}"><span>{mark}</span><strong>{escape(text)}</strong></div>'

def reason_block(record: dict) -> str:
    below = bool(record.get("below_sma200w")); near_min = bool(record.get("near_hist_min_w")); near_lr = bool(record.get("near_linreg_lower"))
    return '<div class="reason-lines">' + reason_line(below, "Sotto SMA200W") + reason_line(near_min, "Vicino al Min W Storico") + reason_line(near_lr, "LinReg Lower vicino" if near_lr else "LinReg Lower non ancora vicino") + '</div>'

def linreg_top_pct(value, lower, upper) -> float | None:
    v = safe_float(value); lo = safe_float(lower); hi = safe_float(upper)
    if v is None or lo is None or hi is None or hi <= lo: return None
    return max(8.0, min(92.0, 92.0 - ((v - lo) / (hi - lo)) * 84.0))

def linreg_section(record: dict, currency: str) -> str:
    if not record.get("linreg_available"):
        return '<div class="compact-section"><div class="section-head"><h4>LinReg W</h4></div><div class="missing-box">' + escape(str(record.get("linreg_error") or "Non disponibile")) + '</div></div>'
    lower = safe_float(record.get("linreg_lower_w")); mid = safe_float(record.get("linreg_mid_w")); upper = safe_float(record.get("linreg_upper_w")); price = safe_float(record.get("last_price"))
    method = str(record.get("linreg_method") or "LinReg 100 close 2 2"); weeks = str(record.get("linreg_weeks") or "N/D")
    upper_top = linreg_top_pct(upper, lower, upper); mid_top = linreg_top_pct(mid, lower, upper); lower_top = linreg_top_pct(lower, lower, upper); price_top = linreg_top_pct(price, lower, upper)
    if None in (upper_top, mid_top, lower_top, price_top):
        return '<div class="compact-section"><div class="section-head"><h4>LinReg W</h4></div><div class="missing-box">LinReg disponibile ma valori non validi per il grafico.</div></div>'
    relation = "Prezzo sopra la Lower e sotto la Mid"
    if price is not None and lower is not None and price < lower: relation = "Prezzo sotto la Lower"
    elif price is not None and mid is not None and upper is not None and mid <= price <= upper: relation = "Prezzo sopra la Mid"
    elif price is not None and upper is not None and price > upper: relation = "Prezzo sopra la Upper"
    html = '<div class="compact-section linreg-section"><div class="section-head"><h4>LinReg W</h4></div>'
    html += f'<p class="linreg-anchor">{escape(method)} - {escape(weeks)} settimane</p><div class="linreg-level-chart">'
    for label, value, top, css in [("UPPER", upper, upper_top, "upper"), ("MID", mid, mid_top, "mid"), ("LOWER", lower, lower_top, "lower")]:
        html += f'<div class="linreg-level-line level-{css}" style="top:{top:.2f}%"><span class="linreg-level-label">{label}</span><span class="linreg-level-value">{escape(fmt_price(value, currency))}</span></div>'
    html += f'<div class="linreg-price-line" style="top:{price_top:.2f}%"><span class="linreg-price-badge">Prezzo {escape(fmt_price(price, currency))}</span></div></div>'
    html += f'<div class="linreg-interpretation">{escape(relation)}</div></div>'
    return html

def technical_details(record: dict, currency: str) -> str:
    html = '<div class="details-compact">'
    html += detail_item("SMA200W", fmt_price(record.get("sma200w"), currency))
    html += detail_item("Hist Min W", fmt_pct(record.get("hist_min_w_pct"), 1))
    html += detail_item("MinW Low", f"{fmt_price(record.get('hist_min_w_low'), currency)} ({record.get('hist_min_w_date') or 'N/D'})")
    html += detail_item("Eq MinW", fmt_price(record.get("hist_min_equivalent"), currency))
    html += detail_item("Hist Max W", fmt_pct(record.get("hist_max_w_pct"), 1))
    html += '</div>'
    return html

def forecast_bar_top(value, low, high) -> float:
    v = safe_float(value); lo = safe_float(low); hi = safe_float(high)
    if v is None or lo is None or hi is None or hi <= lo:
        return 50.0
    return max(8.0, min(92.0, 92.0 - ((v - lo) / (hi - lo)) * 84.0))

def signed_delta_value(target, current) -> str:
    t = safe_float(target); c = safe_float(current)
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
    pct_avg = ((mean-current)/current*100) if current else None
    pct_max = ((high-current)/current*100) if current else None
    pct_min = ((low-current)/current*100) if current else None
    scale_low = min(low, current)
    scale_high = max(high, mean, current)
    max_top = forecast_bar_top(high, scale_low, scale_high)
    avg_top = forecast_bar_top(mean, scale_low, scale_high)
    cur_top = forecast_bar_top(current, scale_low, scale_high)
    min_top = forecast_bar_top(low, scale_low, scale_high)
    min_label_top = min(92.0, min_top + 8.0)
    current_label_top = min(92.0, cur_top + 16.0)
    history_path = escape(forecast_history_path(cur_top), quote=True)
    return (
        '<div class="forecast-loaded">'
        '<div class="forecast-head"><div><div class="forecast-eyebrow">Price target</div>'
        f'<div class="forecast-main"><strong>{mean:.2f}</strong><span>{escape(currency)}</span><em>{escape(signed_delta_value(mean,current))}</em><em>{escape(fmt_pct(pct_avg,2))}</em></div></div>'
        f'<p>{escape(str(analysts))} analisti · Max {high:.2f} · Min {low:.2f}</p></div>'
        '<div class="forecast-chart">'
        f'<svg class="forecast-history" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="{history_path}"/></svg>'
        f'<div class="forecast-anchor" style="top:{cur_top}%"></div>'
        f'<div class="forecast-cone forecast-green" style="clip-path:polygon(0% {cur_top}%,100% {max_top}%,100% {avg_top}%)"></div>'
        f'<div class="forecast-cone forecast-red" style="clip-path:polygon(0% {cur_top}%,100% {avg_top}%,100% {min_top}%)"></div>'
        f'<div class="forecast-line current" style="top:{cur_top}%"></div>'
        f'<div class="forecast-current-solid" style="top:{cur_top}%"></div>'
        f'<div class="forecast-label max" style="top:{max_top}%"><b>Max {escape(fmt_pct(pct_max,2))}</b><strong>{high:.2f}</strong></div>'
        f'<div class="forecast-label avg" style="top:{avg_top}%"><b>Avg {escape(fmt_pct(pct_avg,2))}</b><strong>{mean:.2f}</strong></div>'
        f'<div class="forecast-label min" style="top:{min_label_top}%"><b>Min {escape(fmt_pct(pct_min,2))}</b><strong>{low:.2f}</strong></div>'
        f'<div class="forecast-label current-l" style="top:{current_label_top}%"><b>Current</b><strong>{current:.2f}</strong></div>'
        '<div class="forecast-date forecast-date-left">2026</div><div class="forecast-date forecast-date-mid">Jul</div><div class="forecast-date forecast-date-right">2027</div>'
        '</div></div>'
    )

def open_target_page_from_record(record: dict) -> None:
    st.session_state["target_selected"] = {
        "yf_symbol": str(record.get("yahoo") or "").strip().upper(),
        "ticker": str(record.get("ticker") or "").strip().upper(),
        "tv_symbol": str(record.get("tv") or "").strip().upper(),
        "name": str(record.get("name") or "").strip(),
        "market": str(record.get("tv") or "").split(":", 1)[0].upper() if ":" in str(record.get("tv") or "") else "",
        "currency": str(record.get("currency") or "").strip().upper(),
        "source": "direct",
    }
    st.session_state["target_source"] = "direct"
    st.switch_page("pages/target_analisti.py")

def render_forecast_on_demand(record: dict, rank: int) -> None:
    key = _forecast_key(record)
    title = f"Price Target Forecast · {record.get('ticker', '-') }"
    with st.expander(title, expanded=False):
        url = _forecast_url(record)
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
        with c1:
            if st.button("Scarica dati forecast", key=f"download_forecast_{rank}_{record.get('yahoo','')}"):
                yf_symbol = str(record.get("yahoo") or "").strip().upper()
                tv_symbol = str(record.get("tv") or "").strip().upper()
                ticker = str(record.get("ticker") or "").strip().upper()
                market = tv_symbol.split(":", 1)[0] if ":" in tv_symbol else ""
                with st.spinner(f"Scarico forecast {ticker or yf_symbol}..."):
                    result = fetch_yfinance_targets(yf_symbol, ticker=ticker, market=market, currency=str(record.get("currency") or ""), tv_symbol=tv_symbol)
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
            if st.button("Target Analisti", key=f"target_page_{rank}_{record.get('yahoo','')}", use_container_width=True):
                open_target_page_from_record(record)

def card(record: dict, rank: int) -> str:
    currency = str(record.get("currency") or "").upper(); ticker = str(record.get("ticker") or ""); name = str(record.get("name") or "")
    label = str(record.get("technical_label") or "Monitor tecnico"); count = int(record.get("confluence_count") or 0); tv_url = escape(str(record.get("tradingview_url") or "#"), quote=True)
    card_class = "is-buy" if count == 3 else "is-watch" if count == 2 else "is-monitor"; badge_class = "badge-buy" if count == 3 else "badge-watch" if count == 2 else "badge-monitor"
    html = f'<div class="redesign-card {card_class}"><div class="card-top"><div class="rank">#{rank}</div><div class="identity"><div class="ticker-row"><strong>{escape(ticker)}</strong></div><div class="company-name">{escape(name)}</div></div><div class="status-badge {badge_class}">{escape(label)} <span>{count}/3</span></div></div>'
    html += f'<div class="decision-row"><div class="price-main"><span>Prezzo</span><strong>{escape(fmt_price(record.get("last_price"), currency))}</strong><small class="{vclass(record.get("daily_change_pct"))}">Daily {escape(fmt_pct(record.get("daily_change_pct"), 2))}</small></div><div class="decision-text"><span>Motivo principale</span>{reason_block(record)}</div></div>'
    html += '<div class="condition-metrics-row">'
    html += condition_metric("Distanza SMA200W", fmt_pct(record.get("dist_pct"), 2), fmt_price(record.get("sma200w"), currency), bool(record.get("below_sma200w")), vclass(record.get("dist_pct")))
    html += condition_metric("Scarto Min W Hist", fmt_pct(record.get("gap_points"), 1), fmt_price(record.get("hist_min_equivalent"), currency), bool(record.get("near_hist_min_w")), "neutral")
    html += condition_metric("LinReg Lower", fmt_pct(record.get("linreg_dist_lower_pct"), 2), fmt_price(record.get("linreg_lower_w"), currency), bool(record.get("near_linreg_lower")), vclass(record.get("linreg_dist_lower_pct")))
    html += '</div>' + linreg_section(record, currency)
    html += '<details class="details-expander"><summary>Dettagli SMA200W / Storico</summary>' + technical_details(record, currency) + '</details>'
    html += f'<div class="card-actions"><a href="{tv_url}" target="_blank" rel="noopener noreferrer">Apri TradingView</a></div></div>'
    return html

render_standard_page_header(title="BUY ZONE FINDER", subtitle="Scanner tecnico weekly: SMA200W, Min W storico, LinReg Lower W e Forecast on demand.", toggle_label="Vista compatta", toggle_key="linreg_compact_mode", toggle_default=True, refresh_key="linreg_header_refresh", back_key="linreg_header_back", refresh_callback=refresh_scan)
watchlist_data = load_buy_zone_watchlists()
selected_watchlist, selected_symbols = render_watchlist_selector_panel(watchlist_data)
if selected_symbols:
    records = run_full_scan(selected_symbols) if bool(st.session_state.pop(SESSION_SCAN_REQUEST_KEY, False)) else load_cached_scan(selected_symbols)
else:
    st.session_state.pop(SESSION_SCAN_REQUEST_KEY, None)
    records = []
summary = scan_summary(records)
cols = st.columns(4)
summary_items = [("Titoli", str(summary.get("count", 0)), selected_watchlist), ("Buy Zone", str(summary.get("buy_count", 0)), "3/3 condizioni"), ("Watch", str(summary.get("watch_count", 0)), "2/3 condizioni"), ("Sotto SMA200W +\nVicino al Min W\nStorico", str(summary.get("orange_count", 0)), "SMA200W + Min W")]
for col, (summary_label, summary_value, summary_note) in zip(cols, summary_items):
    with col:
        label_html = escape(summary_label).replace("\n", "<br>")
        st.markdown(f'<div class="summary-card"><div class="summary-label">{label_html}</div><div class="summary-value">{escape(summary_value)}</div><div class="summary-note">{escape(summary_note)}</div></div>', unsafe_allow_html=True)
st.caption(f"Ultimo aggiornamento: {summary.get('last_update', '-')}. Cache 15 minuti. Forecast scaricato solo su richiesta della singola card.")
selected_condition_filter = render_condition_filter(records) if records else "2/3 Watch"
filtered_records = filter_records_by_confluence(records, selected_condition_filter)
st.markdown(f'<div class="section-title">Scanner tecnico <span class="section-watchlist-name">· {escape(selected_watchlist)} · {escape(selected_condition_filter)}</span></div>', unsafe_allow_html=True)
if filtered_records:
    for idx, record in enumerate(filtered_records, 1):
        st.markdown(card(record, idx), unsafe_allow_html=True)
        render_forecast_on_demand(record, idx)
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
