
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
    if file_path.exists(): st.markdown(f"<style>{file_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
local_css(GLOBAL_CSS); local_css(PAGE_CSS); render_app_icon_meta()
def run_full_scan() -> list[dict]:
    bar = st.progress(0, text="Preparazione dati tecnici weekly...")
    def cb(i: int, total: int, item: dict) -> None: bar.progress((i - 1) / max(total, 1), text=f"Calcolo SMA200W/LinReg W {i}/{total}: {item.get('ticker', '')}")
    records = scan_symbols(progress_callback=cb); bar.progress(1.0, text="Scanner tecnico completato"); bar.empty(); return records
def refresh_scan() -> None: st.cache_data.clear(); st.session_state[SESSION_SCAN_REQUEST_KEY] = True; st.rerun()
@st.cache_data(ttl=15 * 60, show_spinner=False)
def load_cached_scan() -> list[dict]: return run_full_scan()
def vclass(value) -> str:
    x = safe_float(value)
    if x is None: return "neutral"
    if x > 0: return "positive"
    if x < 0: return "negative"
    return "neutral"
def detail_item(label: str, value: str, css: str = "") -> str:
    return f'<div class="detail-item"><span class="detail-label">{escape(label)}</span><span class="detail-value {css}">{escape(value)}</span></div>'
def key_metric(label: str, value: str, css: str = "") -> str:
    return f'<div class="key-metric"><span class="key-label">{escape(label)}</span><strong class="key-value {css}">{escape(value)}</strong></div>'
def chip(label: str, active, short_value: str | None = None) -> str:
    css = "chip-on" if bool(active) else "chip-off"; state = "ATTIVO" if bool(active) else "NO"; extra = f'<small>{escape(short_value)}</small>' if short_value else ""
    return f'<div class="condition-chip {css}"><span>{escape(label)}</span><strong>{state}</strong>{extra}</div>'
def sentence_for_record(record: dict) -> str:
    below=bool(record.get("below_sma200w")); near_min=bool(record.get("near_hist_min_w")); near_lr=bool(record.get("near_linreg_lower")); count=int(record.get("confluence_count") or 0); dist_lower=fmt_pct(record.get("linreg_dist_lower_pct"),2)
    if count==3: return "Setup completo: SMA200W, Min W e LinReg Lower sono tutti allineati."
    if below and near_min and not near_lr: return f"Sotto SMA200W e vicino al Min W. Manca LinReg Lower: distanza {dist_lower}."
    if below and near_lr and not near_min: return "Sotto SMA200W e in area LinReg Lower. Non ancora vicino al Min W."
    if near_min and near_lr and not below: return "Vicino a Min W e LinReg Lower, ma non sotto SMA200W."
    if count==1:
        active="SMA200W" if below else "Min W" if near_min else "LinReg Lower" if near_lr else "nessuna"
        return f"Solo una condizione attiva: {active}. Resta in monitoraggio."
    return "Nessuna confluenza tecnica significativa: resta in monitoraggio."
def linreg_bar(record: dict) -> str:
    pos=safe_float(record.get("linreg_position_pct")); style=f"left:{pos:.1f}%;" if pos is not None else "left:0%;"
    return '<div class="linreg-mini-rail"><div class="rail-segment rail-lower">Lower</div><div class="rail-segment rail-mid">Mid</div><div class="rail-segment rail-upper">Upper</div>'+f'<div class="rail-marker" style="{style}"><span>Prezzo</span></div></div>'
def linreg_section(record: dict, currency: str) -> str:
    if not record.get("linreg_available"):
        return '<div class="compact-section"><div class="section-head"><h4>LinReg W</h4></div><div class="missing-box">'+escape(str(record.get("linreg_error") or "Non disponibile"))+'</div></div>'
    method = str(record.get("linreg_method") or "LinReg 100 close 2 2")
    weeks = str(record.get("linreg_weeks") or "N/D")
    html='<div class="compact-section linreg-section"><div class="section-head"><h4>LinReg W</h4></div>'
    html+=f'<p class="linreg-anchor">{escape(method)} - {escape(weeks)} settimane</p>'
    html+='<div class="linreg-strip">'
    html+=detail_item("Lower", fmt_price(record.get("linreg_lower_w"), currency), "positive")
    html+=detail_item("Prezzo", fmt_price(record.get("last_price"), currency), "")
    html+=detail_item("Mid", fmt_price(record.get("linreg_mid_w"), currency), "")
    html+=detail_item("Upper", fmt_price(record.get("linreg_upper_w"), currency), "")
    html+='</div>'+linreg_bar(record)+'</div>'
    return html
def technical_details(record: dict, currency: str) -> str:
    html='<div class="details-compact">'
    html+=detail_item("SMA200W", fmt_price(record.get("sma200w"), currency)); html+=detail_item("Hist Min W", fmt_pct(record.get("hist_min_w_pct"), 1)); html+=detail_item("MinW Low", f"{fmt_price(record.get('hist_min_w_low'), currency)} ({record.get('hist_min_w_date') or 'N/D'})"); html+=detail_item("Eq MinW", fmt_price(record.get("hist_min_equivalent"), currency)); html+=detail_item("Hist Max W", fmt_pct(record.get("hist_max_w_pct"), 1)); html+='</div>'; return html
def card(record: dict, rank: int) -> str:
    currency=str(record.get("currency") or "").upper(); ticker=str(record.get("ticker") or ""); name=str(record.get("name") or ""); label=str(record.get("technical_label") or "Monitor tecnico"); count=int(record.get("confluence_count") or 0); tv_url=escape(str(record.get("tradingview_url") or "#"), quote=True)
    card_class="is-buy" if count==3 else "is-watch" if count==2 else "is-monitor"; badge_class="badge-buy" if count==3 else "badge-watch" if count==2 else "badge-monitor"
    html=f'<div class="redesign-card {card_class}"><div class="card-top"><div class="rank">#{rank}</div><div class="identity"><div class="ticker-row"><strong>{escape(ticker)}</strong></div><div class="company-name">{escape(name)}</div></div><div class="status-badge {badge_class}">{escape(label)} <span>{count}/3</span></div></div>'
    html+=f'<div class="decision-row"><div class="price-main"><span>Prezzo</span><strong>{escape(fmt_price(record.get("last_price"),currency))}</strong><small class="{vclass(record.get("daily_change_pct"))}">Daily {escape(fmt_pct(record.get("daily_change_pct"),2))}</small></div><div class="decision-text"><span>Motivo principale</span><p>{escape(sentence_for_record(record))}</p></div></div>'
    html+='<div class="chips-row">'+chip("SMA200W",record.get("below_sma200w"),fmt_pct(record.get("dist_pct"),1))+chip("Min W",record.get("near_hist_min_w"),fmt_pct(record.get("gap_points"),1))+chip("LinReg Lower",record.get("near_linreg_lower"),fmt_pct(record.get("linreg_dist_lower_pct"),1))+'</div>'
    html+='<div class="key-metrics-row">'+key_metric("Distanza SMA200W",fmt_pct(record.get("dist_pct"),2),vclass(record.get("dist_pct")))+key_metric("Scarto Min W",fmt_pct(record.get("gap_points"),1),"")+key_metric("Distanza Lower",fmt_pct(record.get("linreg_dist_lower_pct"),2),vclass(record.get("linreg_dist_lower_pct")))+'</div>'
    html+=linreg_section(record,currency)+'<details class="details-expander"><summary>Dettagli SMA200W / Storico</summary>'+technical_details(record,currency)+'</details>'+f'<div class="card-actions"><a href="{tv_url}" target="_blank" rel="noopener noreferrer">Apri TradingView</a></div></div>'
    return html
render_standard_page_header(title="Scanner SMA200W / LinReg W", subtitle="Vista decisionale: SMA200W, Min W e LinReg Lower W.", toggle_label="Vista compatta", toggle_key="linreg_compact_mode", toggle_default=True, refresh_key="linreg_header_refresh", back_key="linreg_header_back", refresh_callback=refresh_scan)
records=run_full_scan() if bool(st.session_state.pop(SESSION_SCAN_REQUEST_KEY,False)) else load_cached_scan(); summary=scan_summary(records)
cols=st.columns(4)
for col,(label,value,note) in zip(cols,[("Titoli",str(summary.get("count",0)),"solo azioni"),("Buy Zone",str(summary.get("buy_count",0)),"3/3 condizioni"),("Watch",str(summary.get("watch_count",0)),"2/3 condizioni"),("Area arancione",str(summary.get("orange_count",0)),"SMA200W + Min W")]):
    with col: st.markdown(f'<div class="summary-card"><div class="summary-label">{escape(label)}</div><div class="summary-value">{escape(value)}</div><div class="summary-note">{escape(note)}</div></div>', unsafe_allow_html=True)
st.caption(f"Ultimo aggiornamento: {summary.get('last_update','-')}. Cache 15 minuti.")
st.markdown('<div class="section-title">Scanner tecnico</div>', unsafe_allow_html=True)
if records:
    st.markdown('<div class="redesign-grid">'+''.join(card(record,idx) for idx,record in enumerate(records,1))+'</div>', unsafe_allow_html=True)
else:
    st.warning("Nessun dato disponibile.")
errors=[record for record in records if str(record.get("error") or "").strip()]
if errors:
    with st.expander(f"Titoli con dati tecnici incompleti ({len(errors)})", expanded=False):
        for record in errors: st.write(f"{record.get('ticker','-')}: {record.get('error')}")
