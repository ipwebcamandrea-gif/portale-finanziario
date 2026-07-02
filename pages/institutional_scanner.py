
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
        return "neutral"
    if x > 0:
        return "positive"
    if x < 0:
        return "negative"
    return "neutral"


def fmt_short_price(value, currency: str = "") -> str:
    return fmt_price(value, currency)


def detail_item(label: str, value: str, css: str = "") -> str:
    return (
        '<div class="detail-item">'
        f'<span class="detail-label">{escape(label)}</span>'
        f'<span class="detail-value {css}">{escape(value)}</span>'
        '</div>'
    )


def key_metric(label: str, value: str, css: str = "") -> str:
    return (
        '<div class="key-metric">'
        f'<span class="key-label">{escape(label)}</span>'
        f'<strong class="key-value {css}">{escape(value)}</strong>'
        '</div>'
    )


def chip(label: str, active, short_value: str | None = None) -> str:
    active_bool = bool(active)
    css = "chip-on" if active_bool else "chip-off"
    state = "ATTIVO" if active_bool else "NO"
    extra = f'<small>{escape(short_value)}</small>' if short_value else ""
    return (
        f'<div class="condition-chip {css}">'
        f'<span>{escape(label)}</span>'
        f'<strong>{state}</strong>'
        f'{extra}'
        '</div>'
    )


def sentence_for_record(record: dict) -> str:
    below = bool(record.get("below_sma200w"))
    near_min = bool(record.get("near_hist_min_w"))
    near_lr = bool(record.get("near_linreg_lower"))
    count = int(record.get("confluence_count") or 0)
    dist_lower = fmt_pct(record.get("linreg_dist_lower_pct"), 2)

    if count == 3:
        return "Setup completo: SMA200W, minimo storico W e area LinReg Lower sono tutti allineati."
    if below and near_min and not near_lr:
        return f"Sotto SMA200W e vicino al Min W. Manca LinReg Lower: distanza {dist_lower}."
    if below and near_lr and not near_min:
        return "Sotto SMA200W e in area LinReg Lower. Non ancora vicino al Min W storico."
    if near_min and near_lr and not below:
        return "Vicino a Min W e LinReg Lower, ma non sotto SMA200W."
    if count == 1:
        active = "SMA200W" if below else "Min W" if near_min else "LinReg Lower" if near_lr else "nessuna"
        return f"Solo una condizione attiva: {active}. Resta in monitoraggio."
    return "Nessuna confluenza tecnica significativa: resta in monitoraggio."


def linreg_bar(record: dict) -> str:
    pos = safe_float(record.get("linreg_position_pct"))
    style = f"left:{pos:.1f}%;" if pos is not None else "left:0%;"
    return (
        '<div class="linreg-mini-rail">'
        '<div class="rail-segment rail-lower">Lower</div>'
        '<div class="rail-segment rail-mid">Mid</div>'
        '<div class="rail-segment rail-upper">Upper</div>'
        f'<div class="rail-marker" style="{style}"><span>Prezzo</span></div>'
        '</div>'
    )


def linreg_section(record: dict, currency: str) -> str:
    if not record.get("linreg_available"):
        reason = str(record.get("linreg_error") or "Non disponibile")
        return (
            '<div class="compact-section">'
            '<div class="section-head"><h4>LinReg W</h4></div>'
            f'<div class="missing-box">{escape(reason)}</div>'
            '</div>'
        )

    anchor = ""
    if record.get("linreg_anchor_high") is not None or record.get("linreg_anchor_high_date"):
        anchor = (
            '<p class="linreg-anchor">'
            f'Da Max W {escape(fmt_price(record.get("linreg_anchor_high"), currency))}'
            f' ({escape(str(record.get("linreg_anchor_high_date") or "N/D"))})'
            f' - {escape(str(record.get("linreg_weeks") or "N/D"))} settimane'
            '</p>'
        )

    html = '<div class="compact-section linreg-section">'
    html += '<div class="section-head"><h4>LinReg W - trend corrente</h4></div>'
    html += anchor
    html += '<div class="linreg-strip">'
    html += detail_item("Lower", fmt_price(record.get("linreg_lower_w"), currency), "positive")
    html += detail_item("Prezzo", fmt_price(record.get("last_price"), currency), "")
    html += detail_item("Mid", fmt_price(record.get("linreg_mid_w"), currency), "")
    html += detail_item("Upper", fmt_price(record.get("linreg_upper_w"), currency), "")
    html += '</div>'
    html += linreg_bar(record)
    html += '</div>'
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
    html += f'<strong>{escape(fmt_short_price(record.get("last_price"), currency))}</strong>'
    html += f'<small class="{vclass(record.get("daily_change_pct"))}">Daily {escape(fmt_pct(record.get("daily_change_pct"), 2))}</small>'
    html += '</div>'
    html += '<div class="decision-text">'
    html += f'<span>Motivo principale</span><p>{escape(sentence_for_record(record))}</p>'
    html += '</div>'
    html += '</div>'

    html += '<div class="chips-row">'
    html += chip("SMA200W", record.get("below_sma200w"), fmt_pct(record.get("dist_pct"), 1))
    html += chip("Min W", record.get("near_hist_min_w"), fmt_pct(record.get("gap_points"), 1))
    html += chip("LinReg Lower", record.get("near_linreg_lower"), fmt_pct(record.get("linreg_dist_lower_pct"), 1))
    html += '</div>'

    html += '<div class="key-metrics-row">'
    html += key_metric("Distanza SMA200W", fmt_pct(record.get("dist_pct"), 2), vclass(record.get("dist_pct")))
    html += key_metric("Scarto Min W", fmt_pct(record.get("gap_points"), 1), "")
    html += key_metric("Distanza Lower", fmt_pct(record.get("linreg_dist_lower_pct"), 2), vclass(record.get("linreg_dist_lower_pct")))
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
for col, (label, value, note) in zip(cols, summary_items):
    with col:
        st.markdown(
            f'<div class="summary-card"><div class="summary-label">{escape(label)}</div><div class="summary-value">{escape(value)}</div><div class="summary-note">{escape(note)}</div></div>',
            unsafe_allow_html=True,
        )

st.caption(f"Ultimo aggiornamento: {summary.get('last_update', '-')}. Cache 15 minuti.")
st.markdown('<div class="section-title">Scanner tecnico</div>', unsafe_allow_html=True)

if records:
    grid = '<div class="redesign-grid">' + ''.join(card(record, idx) for idx, record in enumerate(records, 1)) + '</div>'
    st.markdown(grid, unsafe_allow_html=True)
else:
    st.warning("Nessun dato disponibile.")

errors = [record for record in records if str(record.get("error") or "").strip()]
if errors:
    with st.expander(f"Titoli con dati tecnici incompleti ({len(errors)})", expanded=False):
        for record in errors:
            st.write(f"{record.get('ticker', '-')}: {record.get('error')}")
