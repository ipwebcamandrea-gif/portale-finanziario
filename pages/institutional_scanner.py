
from __future__ import annotations
from html import escape
from pathlib import Path
import streamlit as st
from components.standard_header import render_standard_page_header
from utils.app_branding import render_app_icon_meta
from utils.auth import require_login
from utils.institutional_scanner import fmt_price, fmt_pct, safe_float, scan_summary, scan_symbols
require_login()
ROOT_DIR=Path(__file__).resolve().parent.parent
for css_path in [ROOT_DIR/"css"/"global.css", ROOT_DIR/"css"/"institutional_scanner.css"]:
    if css_path.exists(): st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
render_app_icon_meta(); SESSION_SCAN_REQUEST_KEY="institutional_scan_requested"
def run_full_scan():
    bar=st.progress(0, text="Preparazione dati tecnici weekly...")
    def cb(i,t,item): bar.progress((i-1)/max(t,1), text=f"Calcolo SMA200W/Fibonacci {i}/{t}: {item.get('ticker','')}")
    out=scan_symbols(progress_callback=cb); bar.progress(1.0, text="Scanner tecnico completato"); bar.empty(); return out
def refresh_scan(): st.cache_data.clear(); st.session_state[SESSION_SCAN_REQUEST_KEY]=True; st.rerun()
@st.cache_data(ttl=15*60, show_spinner=False)
def load_cached_scan(): return run_full_scan()
def cval(v):
    x=safe_float(v); return "institutional-neutral" if x is None else "institutional-positive" if x>0 else "institutional-negative" if x<0 else "institutional-neutral"
def metric(label,value,css="",box=""):
    return f'<div class="institutional-metric {box}"><div class="institutional-mini-label">{escape(label)}</div><div class="institutional-metric-value {css}">{escape(value)}</div></div>'
def zone(label,value,css): return f'<div class="institutional-fib-zone {css}"><div class="institutional-fib-zone-label">{escape(label)}</div><div class="institutional-fib-zone-value">{escape(value)}</div></div>'
def fib_panel(r,cur):
    if not r.get('fib_available'): return '<div class="institutional-fib-panel"><div class="institutional-fib-title">Fibonacci W automatico - Major Swing</div><div class="institutional-fib-missing">Non disponibile</div></div>'
    m=safe_float(r.get('fib_marker_pct')); style=f"left:{m:.1f}%;" if m is not None else "left:0%;"
    html='<div class="institutional-fib-panel"><div class="institutional-fib-title">Fibonacci W automatico - Major Swing</div>'
    html+=f'<div class="institutional-fib-swing">Swing primario automatico - <span class="institutional-negative">Min {escape(fmt_price(r.get("fib_low"),cur))} ({escape(str(r.get("fib_low_date") or "N/D"))})</span> - <span class="institutional-positive">Max {escape(fmt_price(r.get("fib_high"),cur))} ({escape(str(r.get("fib_high_date") or "N/D"))})</span></div>'
    html+='<div class="institutional-fib-levels">'
    for lvl,key in [('0.500','fib_0500'),('0.618','fib_0618'),('0.786','fib_0786'),('0.887','fib_0887')]: html+=f'<span>{lvl}<br><b>{escape(fmt_price(r.get(key),cur))}</b></span>'
    html+='</div><div class="institutional-fib-rail"><div class="institutional-fib-segment-first">FIRST BUY</div><div class="institutional-fib-segment-buy">BUY</div><div class="institutional-fib-segment-strong">STRONG</div>'
    html+=f'<div class="institutional-fib-marker" style="{style}"><span>Prezzo</span></div></div><div class="institutional-fib-zones">'
    html+=zone('First Buy',f"{fmt_price(r.get('fib_first_buy_low'),cur)} - {fmt_price(r.get('fib_first_buy_high'),cur)}",'institutional-fib-zone-first')
    html+=zone('Buy',f"{fmt_price(r.get('fib_buy_low'),cur)} - {fmt_price(r.get('fib_buy_high'),cur)}",'institutional-fib-zone-buy')
    html+=zone('Strong Buy',f"{fmt_price(r.get('fib_strong_low'),cur)} - {fmt_price(r.get('fib_strong_high'),cur)}",'institutional-fib-zone-strong')
    html+=f'</div><div class="institutional-fib-status"><span>Stato Fib</span><strong>{escape(str(r.get("fib_status") or ""))}</strong></div></div>'
    return html
def render_card(r,i):
    cur=str(r.get('currency') or '').upper(); lab=str(r.get('technical_label') or 'Monitor tecnico'); orange='institutional-metric-orange' if r.get('orange_zone') else ''; tv=escape(str(r.get('tradingview_url') or '#'), quote=True)
    label_class='institutional-label-buy' if lab!='Monitor tecnico' else ''
    card_class='institutional-card-buy' if lab!='Monitor tecnico' else ''
    html=f'<div class="institutional-card {card_class}"><div class="institutional-card-header"><div class="institutional-rank">#{i}</div><div class="institutional-title-wrap"><div class="institutional-ticker">{escape(str(r.get("ticker") or ""))}</div><div class="institutional-name">{escape(str(r.get("name") or ""))}</div></div><div class="institutional-label {label_class}">● {escape(lab)}</div></div>'
    html+=f'<div class="institutional-price-status-row"><div class="institutional-price-box"><div class="institutional-mini-label">Prezzo attuale</div><div class="institutional-price-value">{escape(fmt_price(r.get("last_price"),cur))}</div><div class="institutional-daily {cval(r.get("daily_change_pct"))}">Daily {escape(fmt_pct(r.get("daily_change_pct"),2))}</div></div><div class="institutional-status-box"><div class="institutional-mini-label">Stato tecnico</div><div class="institutional-status-value">{escape(lab)}</div><div class="institutional-status-note">SMA200W - minimi storici - Fibonacci W</div></div></div>'
    html+='<div class="institutional-section-mini-title">Area SMA200W / Storico</div><div class="institutional-metrics-grid">'
    html+=metric('SMA200W',fmt_price(r.get('sma200w'),cur),box=orange)+metric('Distanza sotto la SMA200W',fmt_pct(r.get('dist_pct'),2),cval(r.get('dist_pct')),orange)+metric('Area arancione','SI' if r.get('orange_zone') else 'NO',box=orange)+metric('Scarto da Min W',fmt_pct(r.get('gap_points'),1),box=orange)+metric('Hist Min W',fmt_pct(r.get('hist_min_w_pct'),1),box=orange)+metric('MinW Low sotto SMA200W',f"{fmt_price(r.get('hist_min_w_low'),cur)} ({r.get('hist_min_w_date') or 'N/D'})",box=orange)+metric('Eq oggi MinW',fmt_price(r.get('hist_min_equivalent'),cur),box=orange)+metric('Hist Max W',fmt_pct(r.get('hist_max_w_pct'),1),box=orange)
    html+='</div>'+fib_panel(r,cur)+f'<div class="institutional-card-actions"><a href="{tv}" target="_blank" rel="noopener noreferrer">Apri TradingView</a></div></div>'
    return html
render_standard_page_header(title="Scanner SMA200W / Fibonacci", subtitle="Scanner tecnico weekly: SMA200W, minimi storici sotto media e Major Swing Fibonacci W.", toggle_label="📱 Vista compatta", toggle_key="institutional_compact_mode", toggle_default=True, refresh_key="institutional_header_refresh", back_key="institutional_header_back", refresh_callback=refresh_scan)
records=run_full_scan() if bool(st.session_state.pop(SESSION_SCAN_REQUEST_KEY,False)) else load_cached_scan(); s=scan_summary(records)
cols=st.columns(4)
for col,(l,v,n) in zip(cols,[("Titoli analizzati",str(s.get('count',0)),"Solo azioni"),("Area arancione",str(s.get('orange_count',0)),"SMA200W + minimi"),("Dentro Fib",str(s.get('fib_count',0)),"First/Buy/Strong"),("Fib Strong",str(s.get('strong_fib_count',0)),"Zona profonda")]):
    with col: st.markdown(f'<div class="institutional-summary-card"><div class="institutional-summary-label">{escape(l)}</div><div class="institutional-summary-value">{escape(v)}</div><div class="institutional-summary-note">{escape(n)}</div></div>', unsafe_allow_html=True)
st.caption(f"Ultimo aggiornamento: {s.get('last_update','-')}. Lettura live ticker per ticker con cache 15 minuti.")
st.markdown('<div class="institutional-section-title">Scanner tecnico SMA200W / Fibonacci</div>', unsafe_allow_html=True)
st.markdown('<div class="institutional-grid">'+''.join(render_card(r,i) for i,r in enumerate(records,1))+'</div>', unsafe_allow_html=True) if records else st.warning("Nessun dato disponibile.")
errs=[r for r in records if str(r.get('error') or '').strip()]
if errs:
    with st.expander(f"Titoli con dati tecnici incompleti ({len(errs)})", expanded=False):
        for r in errs: st.write(f"{r.get('ticker','-')}: {r.get('error')}")
