
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
        bar.progress((i - 1) / max(total, 1), text=f"Calcolo SMA200W/LinReg W {i}/{total}: {item.get('ticker', '')}")

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
        return "institutional-neutral"
    if x > 0:
        return "institutional-positive"
    if x < 0:
        return "institutional-negative"
    return "institutional-neutral"


def metric(label: str, value: str, css: str = "", box: str = "") -> str:
    return (
        f'<div class="institutional-metric {box}">'
        f'<div class="institutional-mini-label">{escape(label)}</div>'
        f'<div class="institutional-metric-value {css}">{escape(value)}</div>'
        '</div>'
    )


def condition_status(active) -> str:
    return '<span class="condition-on">ATTIVO</span>' if active else '<span class="condition-off">NO</span>'


def linreg_panel(record: dict, currency: str) -> str:
    if not record.get("linreg_available"):
        reason = str(record.get("linreg_error") or "Non disponibile")
        return (
            '<div class="linreg-panel">'
            '<div class="panel-title">LinReg W</div>'
            f'<div class="linreg-missing">{escape(reason)}</div>'
            '</div>'
        )

    pos = safe_float(record.get("linreg_position_pct"))
    marker_style = f"left:{pos:.1f}%;" if pos is not None else "left:0%;"

    anchor_high = record.get("linreg_anchor_high")
    anchor_date = record.get("linreg_anchor_high_date")
    weeks = record.get("linreg_weeks")
    anchor_text = ""
    if anchor_high is not None or anchor_date:
        anchor_text = (
            '<div class="linreg-anchor">'
            f'Canale trend corrente da Max W {escape(fmt_price(anchor_high, currency))}'
            f' ({escape(str(anchor_date or "N/D"))})'
            f' - {escape(str(weeks or "N/D"))} settimane'
            '</div>'
        )

    html = '<div class="linreg-panel"><div class="panel-title">LinReg W</div>'
    html += anchor_text
    html += '<div class="linreg-values">'
    html += metric("Lower W", fmt_price(record.get("linreg_lower_w"), currency), "linreg-lower")
    html += metric("Distanza Lower", fmt_pct(record.get("linreg_dist_lower_pct"), 2), vclass(record.get("linreg_dist_lower_pct")))
    html += metric("Mid W", fmt_price(record.get("linreg_mid_w"), currency))
    html += metric("Upper W", fmt_price(record.get("linreg_upper_w"), currency))
    html += '</div>'
    html += '<div class="linreg-rail">'
    html += '<div class="linreg-lower-zone">Lower</div>'
    html += '<div class="linreg-mid-zone">Mid</div>'
    html += '<div class="linreg-upper-zone">Upper</div>'
    html += f'<div class="linreg-marker" style="{marker_style}"><span>Prezzo</span></div>'
    html += '</div></div>'
    return html


def confluence_panel(record: dict) -> str:
    count = int(record.get("confluence_count") or 0)
    label = str(record.get("technical_label") or "Monitor tecnico")
    return (
        '<div class="confluence-panel">'
        '<div class="panel-title">Confluenza tecnica</div>'
        f'<div class="condition-row"><span>Sotto SMA200W</span>{condition_status(record.get("below_sma200w"))}</div>'
        f'<div class="condition-row"><span>Vicino Min W</span>{condition_status(record.get("near_hist_min_w"))}</div>'
        f'<div class="condition-row"><span>Vicino LinReg Lower</span>{condition_status(record.get("near_linreg_lower"))}</div>'
        f'<div class="confluence-result"><span>{count}/3 condizioni</span><strong>{escape(label)}</strong></div>'
        '</div>'
    )


def render_card(record: dict, rank: int) -> str:
    currency = str(record.get("currency") or "").upper()
    label = str(record.get("technical_label") or "Monitor tecnico")
    confluence_count = int(record.get("confluence_count") or 0)
    card_class = "card-buy" if confluence_count == 3 else "card-watch" if confluence_count == 2 else ""
    label_class = "label-buy" if confluence_count == 3 else "label-watch" if confluence_count == 2 else ""
    orange = "institutional-metric-orange" if record.get("orange_zone") else ""
    tv_url = escape(str(record.get("tradingview_url") or "#"), quote=True)

    html = (
        f'<div class="institutional-card {card_class}">'
        '<div class="institutional-card-header">'
        f'<div class="institutional-rank">#{rank}</div>'
        '<div class="title-wrap">'
        f'<div class="ticker">{escape(str(record.get("ticker") or ""))}</div>'
        f'<div class="name">{escape(str(record.get("name") or ""))}</div>'
        '</div>'
        f'<div class="tech-label {label_class}">{escape(label)}</div>'
        '</div>'
    )

    html += (
        '<div class="price-row">'
        '<div class="price-box">'
        '<div class="institutional-mini-label">Prezzo attuale</div>'
        f'<div class="price-value">{escape(fmt_price(record.get("last_price"), currency))}</div>'
        f'<div class="daily {vclass(record.get("daily_change_pct"))}">Daily {escape(fmt_pct(record.get("daily_change_pct"), 2))}</div>'
        '</div>'
        '<div class="state-box">'
        '<div class="institutional-mini-label">Stato tecnico</div>'
        f'<div class="state-value">{confluence_count}/3</div>'
        '<div class="state-note">SMA200W - Min W - LinReg W</div>'
        '</div>'
        '</div>'
    )

    html += '<div class="section-mini-title">Area SMA200W / Storico</div><div class="institutional-metrics-grid">'
    html += metric("SMA200W", fmt_price(record.get("sma200w"), currency), box=orange)
    html += metric("Distanza SMA200W", fmt_pct(record.get("dist_pct"), 2), vclass(record.get("dist_pct")), orange)
    html += metric("Area arancione", "SI" if record.get("orange_zone") else "NO", box=orange)
    html += metric("Scarto da Min W", fmt_pct(record.get("gap_points"), 1), box=orange)
    html += metric("Hist Min W", fmt_pct(record.get("hist_min_w_pct"), 1), box=orange)
    html += metric("MinW Low", f"{fmt_price(record.get('hist_min_w_low'), currency)} ({record.get('hist_min_w_date') or 'N/D'})", box=orange)
    html += metric("Eq oggi MinW", fmt_price(record.get("hist_min_equivalent"), currency), box=orange)
    html += metric("Hist Max W", fmt_pct(record.get("hist_max_w_pct"), 1), box=orange)
    html += '</div>'

    html += linreg_panel(record, currency)
    html += confluence_panel(record)
    html += f'<div class="institutional-card-actions"><a href="{tv_url}" target="_blank" rel="noopener noreferrer">Apri TradingView</a></div>'
    html += '</div>'
    return html


render_standard_page_header(
    title="Scanner SMA200W / LinReg W",
    subtitle="Scanner tecnico weekly: SMA200W, minimi storici sotto media e regressione lineare weekly.",
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
    ("Titoli", str(summary.get("count", 0)), "Solo azioni"),
    ("Buy Zone", str(summary.get("buy_count", 0)), "3/3 condizioni"),
    ("Watch", str(summary.get("watch_count", 0)), "2/3 condizioni"),
    ("Area arancione", str(summary.get("orange_count", 0)), "SMA200W + minimi"),
]
for col, (label, value, note) in zip(cols, summary_items):
    with col:
        st.markdown(
            f'<div class="summary-card"><div class="summary-label">{escape(label)}</div><div class="summary-value">{escape(value)}</div><div class="summary-note">{escape(note)}</div></div>',
            unsafe_allow_html=True,
        )

st.caption(f"Ultimo aggiornamento: {summary.get('last_update', '-')}. Lettura live ticker per ticker con cache 15 minuti.")
st.markdown('<div class="section-title">Scanner tecnico SMA200W / LinReg W</div>', unsafe_allow_html=True)

# IMPORTANT: no inline conditional expression here.
# The old one-line expression could render the returned Streamlit DeltaGenerator at the bottom of the page.
if records:
    grid_html = '<div class="institutional-grid">' + ''.join(render_card(record, idx) for idx, record in enumerate(records, 1)) + '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)
else:
    st.warning("Nessun dato disponibile.")

errors = [record for record in records if str(record.get("error") or "").strip()]
if errors:
    with st.expander(f"Titoli con dati tecnici incompleti ({len(errors)})", expanded=False):
        for record in errors:
            st.write(f"{record.get('ticker', '-')}: {record.get('error')}")
