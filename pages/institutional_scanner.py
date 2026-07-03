
from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from components.standard_header import render_standard_page_header
from utils.app_branding import render_app_icon_meta
from utils.auth import require_login
from utils.institutional_scanner import fmt_price, fmt_pct, safe_float, scan_summary, scan_symbols

require_login()

ROOT_DIR = Path(__file__).resolve().parent.parent
GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
PAGE_CSS = ROOT_DIR / "css" / "institutional_scanner.css"
SESSION_SCAN_REQUEST_KEY = "technical_linreg_scan_requested"


def local_css(file_path: Path) -> None:
    if file_path.exists():
        st.markdown(f"<style>{file_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


local_css(GLOBAL_CSS)
local_css(PAGE_CSS)
render_app_icon_meta()


def run_full_scan() -> list[dict]:
    bar = st.progress(0, text="Preparazione dati tecnici weekly...")

    def cb(i: int, total: int, item: dict) -> None:
        bar.progress(
            (i - 1) / max(total, 1),
            text=f"Calcolo SMA200W/LinReg W {i}/{total}: {item.get('ticker', '')}",
        )

    records = scan_symbols(progress_callback=cb)
    bar.progress(1.0, text="Scanner tecnico completato")
    bar.empty()
    return records


def refresh_scan() -> None:
    st.cache_data.clear()
    st.session_state[SESSION_SCAN_REQUEST_KEY] = True
    st.rerun()


@st.cache_data(ttl=15 * 60, show_spinner=False)
def load_cached_scan() -> list[dict]:
    return run_full_scan()


def vclass(value) -> str:
    x = safe_float(value)
    if x is None:
        return "neutral"
    if x > 0:
        return "positive"
    if x < 0:
        return "negative"
    return "neutral"


def detail_item(label: str, value: str, css: str = "") -> str:
    return (
        '<div class="detail-item">'
        f'<span class="detail-label">{escape(label)}</span>'
        f'<span class="detail-value {css}">{escape(value)}</span>'
        '</div>'
    )


def condition_metric(
    label: str,
    value: str,
    subvalue: str,
    active: bool,
    value_css: str = "",
) -> str:
    state = "ATTIVO" if active else "NO"
    css = "condition-metric-on" if active else "condition-metric-off"
    return (
        f'<div class="condition-metric {css}">'
        f'<span class="condition-metric-label">{escape(label)}</span>'
        f'<strong class="condition-metric-value {value_css}">{escape(value)}</strong>'
        f'<span class="condition-metric-subvalue">{escape(subvalue)}</span>'
        f'<span class="condition-metric-state">{escape(state)}</span>'
        '</div>'
    )


def reason_line(active: bool, text: str) -> str:
    css = "reason-ok" if active else "reason-ko"
    mark = "✓" if active else "✕"
    return f'<div class="reason-line {css}"><span>{mark}</span><strong>{escape(text)}</strong></div>'


def reason_block(record: dict) -> str:
    below = bool(record.get("below_sma200w"))
    near_min = bool(record.get("near_hist_min_w"))
    near_lr = bool(record.get("near_linreg_lower"))
    return (
        '<div class="reason-lines">'
        + reason_line(below, "Sotto SMA200W")
        + reason_line(near_min, "Vicino al Min W")
        + reason_line(near_lr, "LinReg Lower vicino" if near_lr else "LinReg Lower non ancora vicino")
        + '</div>'
    )


def linreg_top_pct(value, lower, upper) -> float | None:
    v = safe_float(value)
    lo = safe_float(lower)
    hi = safe_float(upper)
    if v is None or lo is None or hi is None or hi <= lo:
        return None
    ratio = (v - lo) / (hi - lo)
    # Keep labels/lines inside the chart. Lower = 92%, Upper = 8%.
    return max(8.0, min(92.0, 92.0 - ratio * 84.0))


def linreg_section(record: dict, currency: str) -> str:
    if not record.get("linreg_available"):
        return (
            '<div class="compact-section">'
            '<div class="section-head"><h4>LinReg W</h4></div>'
            f'<div class="missing-box">{escape(str(record.get("linreg_error") or "Non disponibile"))}</div>'
            '</div>'
        )

    lower = safe_float(record.get("linreg_lower_w"))
    mid = safe_float(record.get("linreg_mid_w"))
    upper = safe_float(record.get("linreg_upper_w"))
    price = safe_float(record.get("last_price"))
    method = str(record.get("linreg_method") or "LinReg 100 close 2 2")
    weeks = str(record.get("linreg_weeks") or "N/D")

    upper_top = linreg_top_pct(upper, lower, upper)
    mid_top = linreg_top_pct(mid, lower, upper)
    lower_top = linreg_top_pct(lower, lower, upper)
    price_top = linreg_top_pct(price, lower, upper)

    if None in (upper_top, mid_top, lower_top, price_top):
        return (
            '<div class="compact-section">'
            '<div class="section-head"><h4>LinReg W</h4></div>'
            '<div class="missing-box">LinReg disponibile ma valori non validi per il grafico.</div>'
            '</div>'
        )

    dist = fmt_pct(record.get("linreg_dist_lower_pct"), 2)
    relation = "Prezzo sopra la Lower e sotto la Mid"
    if price is not None and lower is not None and price < lower:
        relation = "Prezzo sotto la Lower"
    elif price is not None and mid is not None and upper is not None and mid <= price <= upper:
        relation = "Prezzo sopra la Mid"
    elif price is not None and upper is not None and price > upper:
        relation = "Prezzo sopra la Upper"

    html = '<div class="compact-section linreg-section">'
    html += '<div class="section-head"><h4>LinReg W</h4></div>'
    html += f'<p class="linreg-anchor">{escape(method)} - {escape(weeks)} settimane</p>'
    html += '<div class="linreg-level-chart">'

    for label, value, top, css in [
        ("UPPER", upper, upper_top, "upper"),
        ("MID", mid, mid_top, "mid"),
        ("LOWER", lower, lower_top, "lower"),
    ]:
        html += (
            f'<div class="linreg-level-line level-{css}" style="top:{top:.2f}%">'
            f'<span class="linreg-level-label">{label}</span>'
            f'<span class="linreg-level-value">{escape(fmt_price(value, currency))}</span>'
            '</div>'
        )

    html += (
        f'<div class="linreg-price-line" style="top:{price_top:.2f}%">'
        f'<span class="linreg-price-badge">Prezzo {escape(fmt_price(price, currency))}</span>'
        '</div>'
    )
    html += '</div>'
    html += f'<div class="linreg-interpretation">{escape(relation)} · distanza Lower {escape(dist)}</div>'
    html += '</div>'
    return html


def technical_details(record: dict, currency: str) -> str:
    html = '<div class="details-compact">'
    html += detail_item("SMA200W", fmt_price(record.get("sma200w"), currency))
    html += detail_item("Hist Min W", fmt_pct(record.get("hist_min_w_pct"), 1))
    html += detail_item(
        "MinW Low",
        f"{fmt_price(record.get('hist_min_w_low'), currency)} ({record.get('hist_min_w_date') or 'N/D'})",
    )
    html += detail_item("Eq MinW", fmt_price(record.get("hist_min_equivalent"), currency))
    html += detail_item("Hist Max W", fmt_pct(record.get("hist_max_w_pct"), 1))
    html += '</div>'
    return html


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
    html += '<div class="card-top">'
    html += f'<div class="rank">#{rank}</div>'
    html += '<div class="identity">'
    html += f'<div class="ticker-row"><strong>{escape(ticker)}</strong></div>'
    html += f'<div class="company-name">{escape(name)}</div>'
    html += '</div>'
    html += f'<div class="status-badge {badge_class}">{escape(label)} <span>{count}/3</span></div>'
    html += '</div>'

    html += '<div class="decision-row">'
    html += '<div class="price-main">'
    html += '<span>Prezzo</span>'
    html += f'<strong>{escape(fmt_price(record.get("last_price"), currency))}</strong>'
    html += f'<small class="{vclass(record.get("daily_change_pct"))}">Daily {escape(fmt_pct(record.get("daily_change_pct"), 2))}</small>'
    html += '</div>'
    html += '<div class="decision-text">'
    html += '<span>Motivo principale</span>'
    html += reason_block(record)
    html += '</div>'
    html += '</div>'

    html += '<div class="condition-metrics-row">'
    html += condition_metric(
        "Distanza SMA200W",
        fmt_pct(record.get("dist_pct"), 2),
        fmt_price(record.get("sma200w"), currency),
        bool(record.get("below_sma200w")),
        vclass(record.get("dist_pct")),
    )
    html += condition_metric(
        "Scarto Min W",
        fmt_pct(record.get("gap_points"), 1),
        fmt_price(record.get("hist_min_equivalent"), currency),
        bool(record.get("near_hist_min_w")),
        "neutral",
    )
    html += condition_metric(
        "LinReg Lower",
        fmt_pct(record.get("linreg_dist_lower_pct"), 2),
        fmt_price(record.get("linreg_lower_w"), currency),
        bool(record.get("near_linreg_lower")),
        vclass(record.get("linreg_dist_lower_pct")),
    )
    html += '</div>'

    html += linreg_section(record, currency)
    html += '<details class="details-expander">'
    html += '<summary>Dettagli SMA200W / Storico</summary>'
    html += technical_details(record, currency)
    html += '</details>'
    html += f'<div class="card-actions"><a href="{tv_url}" target="_blank" rel="noopener noreferrer">Apri TradingView</a></div>'
    html += '</div>'
    return html


render_standard_page_header(
    title="Scanner SMA200W / LinReg W",
    subtitle="Vista decisionale: SMA200W, Min W e LinReg Lower W.",
    toggle_label="Vista compatta",
    toggle_key="linreg_compact_mode",
    toggle_default=True,
    refresh_key="linreg_header_refresh",
    back_key="linreg_header_back",
    refresh_callback=refresh_scan,
)

records = run_full_scan() if bool(st.session_state.pop(SESSION_SCAN_REQUEST_KEY, False)) else load_cached_scan()
summary = scan_summary(records)

cols = st.columns(4)
summary_items = [
    ("Titoli", str(summary.get("count", 0)), "solo azioni"),
    ("Buy Zone", str(summary.get("buy_count", 0)), "3/3 condizioni"),
    ("Watch", str(summary.get("watch_count", 0)), "2/3 condizioni"),
    ("Area arancione", str(summary.get("orange_count", 0)), "SMA200W + Min W"),
]
for col, (summary_label, summary_value, summary_note) in zip(cols, summary_items):
    with col:
        st.markdown(
            f'<div class="summary-card"><div class="summary-label">{escape(summary_label)}</div>'
            f'<div class="summary-value">{escape(summary_value)}</div>'
            f'<div class="summary-note">{escape(summary_note)}</div></div>',
            unsafe_allow_html=True,
        )

st.caption(f"Ultimo aggiornamento: {summary.get('last_update', '-')}. Cache 15 minuti.")
st.markdown('<div class="section-title">Scanner tecnico</div>', unsafe_allow_html=True)

if records:
    st.markdown(
        '<div class="redesign-grid">' + ''.join(card(record, idx) for idx, record in enumerate(records, 1)) + '</div>',
        unsafe_allow_html=True,
    )
else:
    st.warning("Nessun dato disponibile.")

errors = [record for record in records if str(record.get("error") or "").strip()]
if errors:
    with st.expander(f"Titoli con dati tecnici incompleti ({len(errors)})", expanded=False):
        for record in errors:
            st.write(f"{record.get('ticker', '-')}: {record.get('error')}")
