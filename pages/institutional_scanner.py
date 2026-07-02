from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from components.standard_header import render_standard_page_header
from utils.app_branding import render_app_icon_meta
from utils.auth import require_login
from utils.institutional_scanner import (
    SYMBOLS,
    SLEEP_BETWEEN_TICKERS_SECONDS,
    build_record,
    fmt_num,
    fmt_pct,
    fmt_price,
    safe_float,
    scan_summary,
    sort_priority,
)

require_login()

ROOT_DIR = Path(__file__).resolve().parent.parent
GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
PAGE_CSS = ROOT_DIR / "css" / "institutional_scanner.css"


def local_css(file_path: Path) -> None:
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(f"<style>{file.read()}</style>", unsafe_allow_html=True)

local_css(GLOBAL_CSS)
local_css(PAGE_CSS)
render_app_icon_meta()

SESSION_RECORDS_KEY = "institutional_scan_records"
SESSION_LAST_UPDATE_KEY = "institutional_scan_last_update"
SESSION_SCAN_REQUEST_KEY = "institutional_scan_requested"


def refresh_scan() -> None:
    """Request a full sequential scan on the next rerun.

    No JSON and no Streamlit data cache are used for the scanner page: completed
    records are kept only in st.session_state. This avoids rendering partial
    results and avoids caching temporarily-empty yfinance fundamentals.
    """
    st.session_state[SESSION_SCAN_REQUEST_KEY] = True
    st.rerun()


def run_full_scan_sequential() -> list[dict]:
    """Run the institutional scan ticker by ticker and publish only at the end."""
    symbols = list(SYMBOLS)
    total = len(symbols)
    records: list[dict] = []

    status_box = st.empty()
    progress_bar = st.progress(0, text="Preparazione scan completo...")

    for idx, item in enumerate(symbols, 1):
        ticker = str(item.get("ticker") or item.get("yahoo") or "-")
        name = str(item.get("name") or "")
        status_box.info(
            f"Scan completo in corso... {idx}/{total} · {ticker}"
            + (f" · {name}" if name else "")
        )
        progress_bar.progress((idx - 1) / max(total, 1), text=f"{idx}/{total} · {ticker}")
        records.append(build_record(item))

        if idx < total and SLEEP_BETWEEN_TICKERS_SECONDS > 0:
            import time
            time.sleep(SLEEP_BETWEEN_TICKERS_SECONDS)

    records = sorted(records, key=sort_priority)
    summary = scan_summary(records)
    st.session_state[SESSION_RECORDS_KEY] = records
    st.session_state[SESSION_LAST_UPDATE_KEY] = summary.get("last_update", "-")
    st.session_state[SESSION_SCAN_REQUEST_KEY] = False

    progress_bar.progress(1.0, text="Scan completato. Render risultati...")
    status_box.success(f"Scan completato: {len(records)} titoli analizzati.")
    return records


def get_session_records() -> list[dict]:
    records = st.session_state.get(SESSION_RECORDS_KEY, [])
    return records if isinstance(records, list) else []


def value_class(value) -> str:
    v = safe_float(value)
    if v is None:
        return "institutional-neutral"
    return "institutional-positive" if v > 0 else "institutional-negative" if v < 0 else "institutional-neutral"


def label_class(label: str) -> str:
    if label == "Institutional Buy Zone":
        return "institutional-label institutional-label-buy"
    if label == "Technical Stress":
        return "institutional-label institutional-label-incomplete"
    if label == "Strong Buy Zone":
        return "institutional-label institutional-label-strong"
    if label == "Buy Zone":
        return "institutional-label institutional-label-buy"
    return "institutional-label"


def card_class(label: str) -> str:
    if label == "Institutional Buy Zone":
        return "institutional-card institutional-card-buy"
    if label == "Technical Stress":
        return "institutional-card institutional-card-incomplete"
    if label == "Strong Buy Zone":
        return "institutional-card institutional-card-strong"
    if label == "Buy Zone":
        return "institutional-card institutional-card-buy"
    return "institutional-card"


def label_icon(label: str) -> str:
    if label == "Institutional Buy Zone":
        return "🟢"
    if label == "Technical Stress":
        return "🟠"
    if label == "Fundamental Watch":
        return "🔵"
    if label == "Strong Buy Zone":
        return "🔥"
    if label == "Buy Zone":
        return "🟢"
    if label == "Watch":
        return "🔵"
    return "⚪"


def orange_metric_box_class(record: dict) -> str:
    return "institutional-metric-orange" if bool(record.get("orange_zone")) else ""


def metric_html(label: str, value: str, css_class: str = "", box_class: str = "") -> str:
    value_css = f"institutional-metric-value {css_class}" if css_class else "institutional-metric-value"
    wrapper_css = f"institutional-metric {box_class}" if box_class else "institutional-metric"
    return f'<div class="{wrapper_css}"><div class="institutional-mini-label">{escape(label)}</div><div class="{value_css}">{escape(value)}</div></div>'


def component_html(label: str, value) -> str:
    return metric_html(label, "N/D" if value is None else fmt_num(value, 1))


def hist_date_text(value) -> str:
    text = str(value or "").strip()
    return text[:10] if text else "N/D"


def hist_price_date_text(price_value, currency: str, date_value) -> str:
    price_text = fmt_price(price_value, currency)
    date_text = hist_date_text(date_value)
    if price_text == "N/D" and date_text == "N/D":
        return "N/D"
    if date_text == "N/D":
        return price_text
    return f"{price_text} ({date_text})"


def data_panel_html(record: dict) -> str:
    label = str(record.get("data_quality_label") or "Dati parziali")
    ratio = safe_float(record.get("data_quality_ratio"))
    pct = f"{ratio * 100:.0f}%" if ratio is not None else "N/D"
    missing_groups = ", ".join(record.get("data_missing_groups") or [])
    if record.get("data_complete"):
        return f'<div class="institutional-data-ok">{escape(label)} · copertura fondamentali {escape(pct)} · score calcolato normalmente</div>'
    suffix = f" · mancanti: {escape(missing_groups)}" if missing_groups else ""
    return f'<div class="institutional-data-warning">{escape(label)} · copertura fondamentali {escape(pct)} · score calcolato con i dati disponibili{suffix}</div>'


def render_card(record: dict, rank: int) -> str:
    ticker = escape(str(record.get("ticker") or ""))
    name = escape(str(record.get("name") or ""))
    label = str(record.get("display_label") or record.get("score_label") or "Monitor")
    currency = str(record.get("currency") or "").upper()
    score = fmt_num(record.get("score_total"), 1)
    price = fmt_price(record.get("last_price"), currency)
    daily = fmt_pct(record.get("daily_change_pct"), 2)
    daily_class = value_class(record.get("daily_change_pct"))
    tv_url = escape(str(record.get("tradingview_url") or "#"), quote=True)
    notes = escape(str(record.get("score_notes") or "-") or "-")
    orange_box = orange_metric_box_class(record)
    hist_orange_box = orange_box
    hist_min_w = fmt_pct(record.get("hist_min_w_pct"), 1)
    hist_gap_from_min = fmt_pct(record.get("gap_points"), 1)
    hist_min_low = hist_price_date_text(record.get("hist_min_w_low"), currency, record.get("hist_min_w_date"))
    hist_min_eq = fmt_price(record.get("hist_min_equivalent"), currency)
    hist_max_w = fmt_pct(record.get("hist_max_w_pct"), 1)
    hist_max_high = hist_price_date_text(record.get("hist_max_w_high"), currency, record.get("hist_max_w_date"))
    hist_max_eq = fmt_price(record.get("hist_max_equivalent"), currency)
    fair_value = fmt_price(record.get("fair_value_composite"), currency)
    margin_safety = fmt_pct(record.get("required_margin_safety_pct"), 1)
    fundamental_buy = fmt_price(record.get("fundamental_buy_price"), currency)
    upside_fv = fmt_pct(record.get("upside_to_fair_value_pct"), 1)
    institutional_zone_text = str(record.get("institutional_buy_zone_text") or "dati insufficienti")
    institutional_status_text = str(record.get("institutional_buy_zone_status_text") or "N/D")
    error = str(record.get("error") or "").strip()

    card = (
        f'<div class="{card_class(label)}">'
        '<div class="institutional-card-header">'
        f'<div class="institutional-rank">#{rank}</div>'
        '<div class="institutional-title-wrap">'
        f'<div class="institutional-ticker">{ticker}</div>'
        f'<div class="institutional-name">{name}</div>'
        '</div>'
        f'<div class="{label_class(label)}">{label_icon(label)} {escape(label)}</div>'
        '</div>'
        f'{data_panel_html(record)}'
        '<div class="institutional-price-score-row">'
        '<div class="institutional-price-box">'
        '<div class="institutional-mini-label">Prezzo attuale</div>'
        f'<div class="institutional-price-value">{escape(price)}</div>'
        f'<div class="institutional-daily {daily_class}">Daily {escape(daily)}</div>'
        '</div>'
        '<div class="institutional-score-box">'
        '<div class="institutional-mini-label">Score</div>'
        f'<div class="institutional-score-value">{escape(score)}</div>'
        '<div class="institutional-score-suffix">/100</div>'
        '</div>'
        '</div>'
        '<div class="institutional-metrics-grid">'
        + metric_html("SMA200W", fmt_price(record.get("sma200w"), currency), box_class=orange_box)
        + metric_html("Distanza sotto la SMA200W", fmt_pct(record.get("dist_pct"), 2), value_class(record.get("dist_pct")), orange_box)
        + metric_html("Hist Min W", hist_min_w, box_class=hist_orange_box)
        + metric_html("Scarto da Min W", hist_gap_from_min, box_class=hist_orange_box)
        + metric_html("MinW Low sotto SMA200W", hist_min_low, box_class=hist_orange_box)
        + metric_html("Eq oggi MinW", hist_min_eq, box_class=hist_orange_box)
        + metric_html("Fair Value composito", fair_value)
        + metric_html("Margine sicurezza", margin_safety)
        + metric_html("Fundamental Buy Price", fundamental_buy)
        + metric_html("Upside vs Fair Value", upside_fv, value_class(record.get("upside_to_fair_value_pct")))
        + metric_html("Fwd P/E", fmt_num(record.get("forward_pe"), 1))
        + metric_html("FCF Yield", fmt_pct(record.get("fcf_yield_pct"), 1), value_class(record.get("fcf_yield_pct")))
        + '</div>'
        '<div class="institutional-components-grid">'
        + component_html("Tecnico", record.get("score_technical"))
        + component_html("Valutazione", record.get("score_valuation"))
        + component_html("Qualità", record.get("score_quality"))
        + component_html("Crescita", record.get("score_growth"))
        + component_html("Rischio/Mom.", record.get("score_risk_momentum"))
        + '</div>'
        '<div class="institutional-range-panel">'
        '<div class="institutional-range-title">Institutional Buy Zone</div>'
        '<div class="institutional-range-grid">'
        f'<div class="institutional-range-box institutional-range-buy"><div class="institutional-range-label">Institutional Buy Zone</div><div class="institutional-range-value">{escape(institutional_zone_text)}</div></div>'
        f'<div class="institutional-range-box institutional-range-strong"><div class="institutional-range-label">Stato attuale</div><div class="institutional-range-value">{escape(institutional_status_text)}</div></div>'
        '</div>'
        '</div>'
        f'<div class="institutional-notes">Motivi: {notes}</div>'
        f'<div class="institutional-card-actions"><a href="{tv_url}" target="_blank" rel="noopener noreferrer">Apri TradingView →</a></div>'
    )
    if error:
        card += f'<div class="institutional-error-box">Dato tecnico incompleto: {escape(error)}</div>'
    return card + '</div>'

render_standard_page_header(
    title="Institutional Scanner",
    subtitle="Tutti i titoli Mega Cap USA/ETF · score parziale stile script locale, area arancione e range operativo.",
    toggle_label="📱 Vista compatta",
    toggle_key="institutional_compact_mode",
    toggle_default=True,
    refresh_key="institutional_header_refresh",
    back_key="institutional_header_back",
    refresh_callback=refresh_scan,
)

scan_requested = bool(st.session_state.pop(SESSION_SCAN_REQUEST_KEY, False))
if scan_requested:
    records = run_full_scan_sequential()
else:
    records = get_session_records()

if not records:
    st.info(
        "Nessuno scan completo presente in questa sessione. "
        "Premi 🔄 Aggiorna per avviare uno scan sequenziale ticker per ticker. "
        "I risultati verranno mostrati solo a scan completato."
    )
    st.stop()

summary = scan_summary(records)

cols = st.columns(4)
summary_cards = [
    ("Titoli analizzati", str(summary.get("count", 0)), "Mostrati tutti"),
    ("Institutional", str(summary.get("institutional_count", 0)), "Dentro Institutional Buy Zone"),
    ("Technical Stress", str(summary.get("technical_stress_count", 0)), "Area tecnica/storica"),
    ("Dati parziali", str(summary.get("partial_count", 0)), "Score comunque calcolato"),
]
for col, (label, value, note) in zip(cols, summary_cards):
    with col:
        st.markdown(
            '<div class="institutional-summary-card">'
            f'<div class="institutional-summary-label">{escape(label)}</div>'
            f'<div class="institutional-summary-value">{escape(value)}</div>'
            f'<div class="institutional-summary-note">{escape(note)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

last_update = st.session_state.get(SESSION_LAST_UPDATE_KEY) or summary.get("last_update", "-")
st.caption(
    f"Ultimo scan completo in sessione: {last_update}. "
    f"Mostro tutti i {len(records)} titoli analizzati. "
    "Lo scan del portale ora è sequenziale come lo script locale: ticker per ticker, "
    "nessun JSON e nessun risultato parziale mostrato durante il calcolo. "
    "Usa 🔄 per avviare un nuovo scan completo."
)
st.markdown('<div class="institutional-section-title">🏁 Tutti i titoli analizzati</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="institutional-grid">' + ''.join(render_card(r, i) for i, r in enumerate(records, 1)) + '</div>',
    unsafe_allow_html=True,
)

errors = [r for r in records if str(r.get("error") or "").strip()]
if errors:
    with st.expander(f"⚠️ Titoli con dati tecnici incompleti ({len(errors)})", expanded=False):
        for r in errors:
            st.write(f"{r.get('ticker', '-')}: {r.get('error')}")
