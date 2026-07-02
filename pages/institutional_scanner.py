from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from components.standard_header import render_standard_page_header
from utils.app_branding import render_app_icon_meta
from utils.auth import require_login
from utils.institutional_scanner import (
    fmt_price,
    fmt_pct,
    safe_float,
    scan_summary,
    scan_symbols,
)

require_login()

ROOT_DIR = Path(__file__).resolve().parent.parent
GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
PAGE_CSS = ROOT_DIR / "css" / "institutional_scanner.css"
SESSION_SCAN_REQUEST_KEY = "institutional_scan_requested"


def local_css(file_path: Path) -> None:
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(f"<style>{file.read()}</style>", unsafe_allow_html=True)

local_css(GLOBAL_CSS)
local_css(PAGE_CSS)
render_app_icon_meta()


def run_full_scan() -> list[dict]:
    progress = st.progress(0, text="Preparazione scanner tecnico...")
    def on_progress(idx: int, total: int, item: dict) -> None:
        progress.progress((idx - 1) / max(total, 1), text=f"Analisi {idx}/{total}: {item.get('ticker', '')}")
    records = scan_symbols(progress_callback=on_progress)
    progress.progress(1.0, text="Scanner completato")
    progress.empty()
    return records


def refresh_scan() -> None:
    st.cache_data.clear()
    st.session_state[SESSION_SCAN_REQUEST_KEY] = True
    st.rerun()


@st.cache_data(ttl=15 * 60, show_spinner=False)
def load_cached_scan() -> list[dict]:
    return run_full_scan()


def value_class(value) -> str:
    v = safe_float(value)
    if v is None: return "institutional-neutral"
    return "institutional-positive" if v > 0 else "institutional-negative" if v < 0 else "institutional-neutral"


def metric_html(label: str, value: str, css_class: str = "", box_class: str = "") -> str:
    value_css = f"institutional-metric-value {css_class}" if css_class else "institutional-metric-value"
    wrapper_css = f"institutional-metric {box_class}" if box_class else "institutional-metric"
    return f'<div class="{wrapper_css}"><div class="institutional-mini-label">{escape(label)}</div><div class="{value_css}">{escape(value)}</div></div>'


def fib_zone_html(label: str, value: str, css_class: str) -> str:
    return f'<div class="institutional-fib-zone {css_class}"><div class="institutional-fib-zone-label">{escape(label)}</div><div class="institutional-fib-zone-value">{escape(value)}</div></div>'


def render_fib_panel(record: dict, currency: str) -> str:
    if not record.get("fib_available"):
        return '<div class="institutional-fib-panel"><div class="institutional-fib-title">Fibonacci W automatico</div><div class="institutional-fib-missing">Non disponibile</div></div>'
    marker = safe_float(record.get("fib_marker_pct"))
    marker_style = f"left:{marker:.1f}%;" if marker is not None else "left:0%;"
    status = str(record.get("fib_status") or "dati insufficienti")
    first = f"{fmt_price(record.get('fib_first_buy_low'), currency)} - {fmt_price(record.get('fib_first_buy_high'), currency)}"
    buy = f"{fmt_price(record.get('fib_buy_low'), currency)} - {fmt_price(record.get('fib_buy_high'), currency)}"
    strong = f"{fmt_price(record.get('fib_strong_low'), currency)} - {fmt_price(record.get('fib_strong_high'), currency)}"
    return (
        '<div class="institutional-fib-panel">'
        '<div class="institutional-fib-title">Fibonacci W automatico</div>'
        '<div class="institutional-fib-swing">Swing da ciclo sotto SMA200W completato · '
        f'<span class="institutional-negative">Min {escape(fmt_price(record.get("fib_low"), currency))} ({escape(str(record.get("fib_low_date") or "N/D"))})</span> → '
        f'<span class="institutional-positive">Max {escape(fmt_price(record.get("fib_high"), currency))} ({escape(str(record.get("fib_high_date") or "N/D"))})</span></div>'
        '<div class="institutional-fib-levels">'
        f'<span>0.500<br><b>{escape(fmt_price(record.get("fib_0500"), currency))}</b></span>'
        f'<span>0.618<br><b>{escape(fmt_price(record.get("fib_0618"), currency))}</b></span>'
        f'<span>0.786<br><b>{escape(fmt_price(record.get("fib_0786"), currency))}</b></span>'
        f'<span>0.887<br><b>{escape(fmt_price(record.get("fib_0887"), currency))}</b></span>'
        '</div>'
        '<div class="institutional-fib-rail"><div class="institutional-fib-segment-first">FIRST BUY</div><div class="institutional-fib-segment-buy">BUY</div><div class="institutional-fib-segment-strong">STRONG</div>'
        f'<div class="institutional-fib-marker" style="{marker_style}"><span>Prezzo</span></div></div>'
        '<div class="institutional-fib-zones">'
        + fib_zone_html("Fib First Buy Area", first, "institutional-fib-zone-first")
        + fib_zone_html("Fib Buy Area", buy, "institutional-fib-zone-buy")
        + fib_zone_html("Fib Strong Buy Area", strong, "institutional-fib-zone-strong")
        + '</div>'
        f'<div class="institutional-fib-status"><span>Stato prezzo Fib</span><strong>{escape(status)}</strong></div>'
        '</div>'
    )


def card_class(record: dict) -> str:
    label = str(record.get("technical_label") or "")
    if label == "Area tecnica forte": return "institutional-card institutional-card-strong"
    if label in {"Area arancione", "Area Fibonacci"}: return "institutional-card institutional-card-buy"
    return "institutional-card"


def label_html(record: dict) -> str:
    label = str(record.get("technical_label") or "Monitor tecnico")
    css = "institutional-label-strong" if label == "Area tecnica forte" else "institutional-label-buy" if label != "Monitor tecnico" else ""
    return f'<div class="institutional-label {css}">● {escape(label)}</div>'


def render_card(record: dict, rank: int) -> str:
    ticker = escape(str(record.get("ticker") or ""))
    name = escape(str(record.get("name") or ""))
    currency = str(record.get("currency") or "").upper()
    orange_box = "institutional-metric-orange" if record.get("orange_zone") else ""
    status = escape(str(record.get("technical_label") or "Monitor tecnico"))
    tv_url = escape(str(record.get("tradingview_url") or "#"), quote=True)
    return (
        f'<div class="{card_class(record)}">'
        '<div class="institutional-card-header">'
        f'<div class="institutional-rank">#{rank}</div><div class="institutional-title-wrap"><div class="institutional-ticker">{ticker}</div><div class="institutional-name">{name}</div></div>{label_html(record)}</div>'
        '<div class="institutional-price-status-row">'
        '<div class="institutional-price-box"><div class="institutional-mini-label">Prezzo attuale</div>'
        f'<div class="institutional-price-value">{escape(fmt_price(record.get("last_price"), currency))}</div><div class="institutional-daily {value_class(record.get("daily_change_pct"))}">Daily {escape(fmt_pct(record.get("daily_change_pct"), 2))}</div></div>'
        '<div class="institutional-status-box"><div class="institutional-mini-label">Stato tecnico</div><div class="institutional-status-value">' + status + '</div><div class="institutional-status-note">SMA200W · minimi storici · Fibonacci W</div></div></div>'
        '<div class="institutional-section-mini-title">Area SMA200W / Storico</div>'
        '<div class="institutional-metrics-grid">'
        + metric_html("SMA200W", fmt_price(record.get("sma200w"), currency), box_class=orange_box)
        + metric_html("Distanza sotto la SMA200W", fmt_pct(record.get("dist_pct"), 2), value_class(record.get("dist_pct")), orange_box)
        + metric_html("Area arancione", "SI" if record.get("orange_zone") else "NO", box_class=orange_box)
        + metric_html("Scarto da Min W", fmt_pct(record.get("gap_points"), 1), box_class=orange_box)
        + metric_html("Hist Min W", fmt_pct(record.get("hist_min_w_pct"), 1), box_class=orange_box)
        + metric_html("MinW Low sotto SMA200W", f"{fmt_price(record.get('hist_min_w_low'), currency)} ({record.get('hist_min_w_date') or 'N/D'})", box_class=orange_box)
        + metric_html("Eq oggi MinW", fmt_price(record.get("hist_min_equivalent"), currency), box_class=orange_box)
        + metric_html("Hist Max W", fmt_pct(record.get("hist_max_w_pct"), 1), box_class=orange_box)
        + '</div>'
        + render_fib_panel(record, currency)
        + f'<div class="institutional-card-actions"><a href="{tv_url}" target="_blank" rel="noopener noreferrer">Apri TradingView →</a></div>'
        '</div>'
    )


render_standard_page_header(
    title="Scanner SMA200W / Fibonacci",
    subtitle="Scanner tecnico weekly: SMA200W, minimi storici sotto media e Fibonacci W automatico.",
    toggle_label="📱 Vista compatta",
    toggle_key="institutional_compact_mode",
    toggle_default=True,
    refresh_key="institutional_header_refresh",
    back_key="institutional_header_back",
    refresh_callback=refresh_scan,
)

scan_requested = bool(st.session_state.pop(SESSION_SCAN_REQUEST_KEY, False))
records = run_full_scan() if scan_requested else load_cached_scan()
summary = scan_summary(records)

cols = st.columns(4)
summary_cards = [
    ("Titoli analizzati", str(summary.get("count", 0)), "Solo azioni"),
    ("Area arancione", str(summary.get("orange_count", 0)), "SMA200W + minimi"),
    ("Dentro Fib", str(summary.get("fib_count", 0)), "First/Buy/Strong"),
    ("Fib Strong", str(summary.get("strong_fib_count", 0)), "Zona profonda"),
]
for col, (label, value, note) in zip(cols, summary_cards):
    with col:
        st.markdown(f'<div class="institutional-summary-card"><div class="institutional-summary-label">{escape(label)}</div><div class="institutional-summary-value">{escape(value)}</div><div class="institutional-summary-note">{escape(note)}</div></div>', unsafe_allow_html=True)

st.caption(f"Ultimo aggiornamento: {summary.get('last_update', '-')}. Lettura live ticker per ticker con cache 15 minuti.")
st.markdown('<div class="institutional-section-title">🏁 Scanner tecnico SMA200W / Fibonacci</div>', unsafe_allow_html=True)

if not records:
    st.warning("Nessun dato disponibile.")
else:
    st.markdown('<div class="institutional-grid">' + ''.join(render_card(r, i) for i, r in enumerate(records, 1)) + '</div>', unsafe_allow_html=True)

errors = [r for r in records if str(r.get("error") or "").strip()]
if errors:
    with st.expander(f"⚠️ Titoli con dati tecnici incompleti ({len(errors)})", expanded=False):
        for r in errors:
            st.write(f"{r.get('ticker', '-')}: {r.get('error')}")
