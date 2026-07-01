from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from components.standard_header import render_standard_page_header
from utils.app_branding import render_app_icon_meta
from utils.auth import require_login
from utils.institutional_scanner import (
    fmt_gap_points,
    fmt_num,
    fmt_pct,
    fmt_price,
    safe_float,
    scan_summary,
    scan_symbols,
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


@st.cache_data(ttl=15 * 60, show_spinner=False)
def load_institutional_scan() -> list[dict]:
    return scan_symbols()


def refresh_scan() -> None:
    st.cache_data.clear()
    st.rerun()


def value_class(value) -> str:
    v = safe_float(value)
    if v is None:
        return "institutional-neutral"
    return "institutional-positive" if v > 0 else "institutional-negative" if v < 0 else "institutional-neutral"


def label_class(label: str) -> str:
    if label == "Strong Buy Zone":
        return "institutional-label institutional-label-strong"
    if label == "Buy Zone":
        return "institutional-label institutional-label-buy"
    return "institutional-label"


def card_class(label: str) -> str:
    if label == "Strong Buy Zone":
        return "institutional-card institutional-card-strong"
    if label == "Buy Zone":
        return "institutional-card institutional-card-buy"
    return "institutional-card"


def label_icon(label: str) -> str:
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
    return (
        f'<div class="{wrapper_css}">'
        f'<div class="institutional-mini-label">{escape(label)}</div>'
        f'<div class="{value_css}">{escape(value)}</div>'
        '</div>'
    )


def render_card(record: dict, rank: int) -> str:
    ticker = escape(str(record.get("ticker") or ""))
    name = escape(str(record.get("name") or ""))
    label = str(record.get("score_label") or "Monitor")
    currency = str(record.get("currency") or "").upper()
    score = fmt_num(record.get("score_total"), 1)
    price = fmt_price(record.get("last_price"), currency)
    daily = fmt_pct(record.get("daily_change_pct"), 2)
    daily_class = value_class(record.get("daily_change_pct"))
    tv_url = escape(str(record.get("tradingview_url") or "#"), quote=True)
    notes = escape(str(record.get("score_notes") or "-") or "-")
    orange_box = orange_metric_box_class(record)
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
        + metric_html("Distanza", fmt_pct(record.get("dist_pct"), 2), value_class(record.get("dist_pct")), orange_box)
        + metric_html("Area arancione", "SI" if record.get("orange_zone") else "NO", box_class=orange_box)
        + metric_html("Scarto da Min W", fmt_gap_points(record.get("gap_points")), box_class=orange_box)
        + metric_html("Fwd P/E", fmt_num(record.get("forward_pe"), 1))
        + metric_html("FCF Yield", fmt_pct(record.get("fcf_yield_pct"), 1), value_class(record.get("fcf_yield_pct")))
        + '</div>'
        '<div class="institutional-range-panel">'
        '<div class="institutional-range-title">Range operativo stimato</div>'
        '<div class="institutional-range-grid">'
        f'<div class="institutional-range-box institutional-range-buy"><div class="institutional-range-label">Buy Zone</div><div class="institutional-range-value">{escape(str(record.get("buy_zone_text") or "dati insufficienti"))}</div></div>'
        f'<div class="institutional-range-box institutional-range-strong"><div class="institutional-range-label">Strong Buy Zone</div><div class="institutional-range-value">{escape(str(record.get("strong_buy_zone_text") or "dati insufficienti"))}</div></div>'
        '</div>'
        '</div>'
        f'<div class="institutional-notes">Motivi: {notes}</div>'
        '<div class="institutional-card-actions">'
        f'<a href="{tv_url}" target="_blank" rel="noopener noreferrer">Apri TradingView →</a>'
        '</div>'
    )
    if error:
        card += f'<div class="institutional-error-box">Dato incompleto: {escape(error)}</div>'
    return card + '</div>'


render_standard_page_header(
    title="Institutional Scanner",
    subtitle="Mega Cap USA/ETF · scoring tecnico/fondamentale · Top 12 istituzionale con range Buy Zone e Strong Buy Zone.",
    toggle_label="📱 Vista compatta",
    toggle_key="institutional_compact_mode",
    toggle_default=True,
    refresh_key="institutional_header_refresh",
    back_key="institutional_header_back",
    refresh_callback=refresh_scan,
)

with st.spinner("Calcolo Institutional Score su Mega Cap USA/ETF..."):
    records = load_institutional_scan()

summary = scan_summary(records)
cols = st.columns(4)
summary_cards = [
    ("Titoli analizzati", str(summary.get("count", 0)), "Lista Mega Cap USA/ETF"),
    ("Top score", fmt_num(summary.get("top_score"), 1), str(summary.get("top_ticker") or "-")),
    ("Buy/Strong", str(summary.get("buy_strong_count", 0)), "Score >= 65"),
    ("Area arancione", str(summary.get("orange_count", 0)), "SMA200W + storico"),
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

st.caption(f"Ultimo aggiornamento pagina: {summary.get('last_update', '-')}. Cache dati: 15 minuti. Usa 🔄 per forzare un nuovo scan.")
st.markdown('<div class="institutional-section-title">🏁 Top 12 per Institutional Score</div>', unsafe_allow_html=True)

if not records:
    st.warning("Nessun dato disponibile per lo scanner istituzionale.")
else:
    st.markdown(
        '<div class="institutional-grid">' + ''.join(render_card(r, i) for i, r in enumerate(records[:12], 1)) + '</div>',
        unsafe_allow_html=True,
    )

errors = [r for r in records if str(r.get("error") or "").strip()]
if errors:
    with st.expander(f"⚠️ Titoli con dati incompleti ({len(errors)})", expanded=False):
        for r in errors:
            st.write(f"{r.get('ticker', '-')}: {r.get('error')}")
