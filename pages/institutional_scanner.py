
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
for css_path in [ROOT_DIR / "css" / "global.css", ROOT_DIR / "css" / "institutional_scanner.css"]:
    if css_path.exists(): st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
render_app_icon_meta()
SESSION_SCAN_REQUEST_KEY = "technical_linreg_scan_requested"
def run_full_scan():
    bar = st.progress(0, text="Preparazione dati tecnici weekly...")
    def cb(i, t, item): bar.progress((i - 1) / max(t, 1), text=f"Calcolo SMA200W/LinReg W {i}/{t}: {item.get('ticker','')}")
    records = scan_symbols(progress_callback=cb)
    bar.progress(1.0, text="Scanner tecnico completato")
    bar.empty()
    return records
def refresh_scan(): st.cache_data.clear(); st.session_state[SESSION_SCAN_REQUEST_KEY] = True; st.rerun()
@st.cache_data(ttl=15*60, show_spinner=False)
def load_cached_scan(): return run_full_scan()
def vclass(v):
    x=safe_float(v); return "institutional-neutral" if x is None else "institutional-positive" if x>0 else "institutional-negative" if x<0 else "institutional-neutral"
def metric(label, value, css="", box=""):
    return f'<div class="institutional-metric {box}"><div class="institutional-mini-label">{escape(label)}</div><div class="institutional-metric-value {css}">{escape(value)}</div></div>'
def status(active): return '<span class="condition-on">ATTIVO</span>' if active else '<span class="condition-off">NO</span>'
def linreg_panel(r, cur):
    if not r.get('linreg_available'):
        return '<div class="linreg-panel"><div class="panel-title">LinReg W</div><div class="linreg-missing">Non disponibile</div></div>'
    pos=safe_float(r.get('linreg_position_pct')); style=f"left:{pos:.1f}%;" if pos is not None else "left:0%;"
    html='<div class="linreg-panel"><div class="panel-title">LinReg W</div>'
    html+='<div class="linreg-values">'
    html+=metric('Lower W', fmt_price(r.get('linreg_lower_w'), cur), 'linreg-lower')
    html+=metric('Distanza Lower', fmt_pct(r.get('linreg_dist_lower_pct'),2), vclass(r.get('linreg_dist_lower_pct')))
    html+=metric('Mid W', fmt_price(r.get('linreg_mid_w'), cur))
    html+=metric('Upper W', fmt_price(r.get('linreg_upper_w'), cur))
    html+='</div><div class="linreg-rail"><div class="linreg-lower-zone">Lower</div><div class="linreg-mid-zone">Mid</div><div class="linreg-upper-zone">Upper</div>'
    html+=f'<div class="linreg-marker" style="{style}"><span>Prezzo</span></div></div></div>'
    return html
def confluence_panel(r):
    count=int(r.get('confluence_count') or 0); label=str(r.get('technical_label') or 'Monitor tecnico')
    return ('<div class="confluence-panel"><div class="panel-title">Confluenza tecnica</div>'
            f'<div class="condition-row"><span>Sotto SMA200W</span>{status(r.get("below_sma200w"))}</div>'
            f'<div class="condition-row"><span>Vicino Min W</span>{status(r.get("near_hist_min_w"))}</div>'
            f'<div class="condition-row"><span>Vicino LinReg Lower</span>{status(r.get("near_linreg_lower"))}</div>'
            f'<div class="confluence-result"><span>{count}/3 condizioni</span><strong>{escape(label)}</strong></div></div>')
def card(r,i):
    cur=str(r.get('currency') or '').upper(); label=str(r.get('technical_label') or 'Monitor tecnico')
    card_class='card-buy' if int(r.get('confluence_count') or 0)==3 else 'card-watch' if int(r.get('confluence_count') or 0)==2 else ''
    label_class='label-buy' if int(r.get('confluence_count') or 0)==3 else 'label-watch' if int(r.get('confluence_count') or 0)==2 else ''
    orange='institutional-metric-orange' if r.get('orange_zone') else ''; tv=escape(str(r.get('tradingview_url') or '#'), quote=True)
    html=f'<div class="institutional-card {card_class}"><div class="institutional-card-header"><div class="institutional-rank">#{i}</div><div class="title-wrap"><div class="ticker">{escape(str(r.get("ticker") or ""))}</div><div class="name">{escape(str(r.get("name") or ""))}</div></div><div class="tech-label {label_class}">{escape(label)}</div></div>'
    html+=f'<div class="price-row"><div class="price-box"><div class="institutional-mini-label">Prezzo attuale</div><div class="price-value">{escape(fmt_price(r.get("last_price"),cur))}</div><div class="daily {vclass(r.get("daily_change_pct"))}">Daily {escape(fmt_pct(r.get("daily_change_pct"),2))}</div></div><div class="state-box"><div class="institutional-mini-label">Stato tecnico</div><div class="state-value">{int(r.get("confluence_count") or 0)}/3</div><div class="state-note">SMA200W + Min W + LinReg W</div></div></div>'
    html+='<div class="section-mini-title">Area SMA200W / Storico</div><div class="institutional-metrics-grid">'
    html+=metric('SMA200W',fmt_price(r.get('sma200w'),cur),box=orange)+metric('Distanza SMA200W',fmt_pct(r.get('dist_pct'),2),vclass(r.get('dist_pct')),orange)+metric('Area arancione','SI' if r.get('orange_zone') else 'NO',box=orange)+metric('Scarto da Min W',fmt_pct(r.get('gap_points'),1),box=orange)+metric('Hist Min W',fmt_pct(r.get('hist_min_w_pct'),1),box=orange)+metric('MinW Low',f"{fmt_price(r.get('hist_min_w_low'),cur)} ({r.get('hist_min_w_date') or 'N/D'})",box=orange)+metric('Eq oggi MinW',fmt_price(r.get('hist_min_equivalent'),cur),box=orange)+metric('Hist Max W',fmt_pct(r.get('hist_max_w_pct'),1),box=orange)
    html+='</div>'+linreg_panel(r,cur)+confluence_panel(r)+f'<div class="institutional-card-actions"><a href="{tv}" target="_blank" rel="noopener noreferrer">Apri TradingView</a></div></div>'
    return html
render_standard_page_header(title='Scanner SMA200W / LinReg W', subtitle='Scanner tecnico weekly: SMA200W, minimi storici sotto media e regressione lineare weekly.', toggle_label='Vista compatta', toggle_key='linreg_compact_mode', toggle_default=True, refresh_key='linreg_header_refresh', back_key='linreg_header_back', refresh_callback=refresh_scan)
records=run_full_scan() if bool(st.session_state.pop(SESSION_SCAN_REQUEST_KEY,False)) else load_cached_scan()
s=scan_summary(records)
cols=st.columns(4)
for col,(l,v,n) in zip(cols,[('Titoli',str(s.get('count',0)),'Solo azioni'),('Buy Zone',str(s.get('buy_count',0)),'3/3 condizioni'),('Watch',str(s.get('watch_count',0)),'2/3 condizioni'),('Area arancione',str(s.get('orange_count',0)),'SMA200W + minimi')]):
    with col: st.markdown(f'<div class="summary-card"><div class="summary-label">{escape(l)}</div><div class="summary-value">{escape(v)}</div><div class="summary-note">{escape(n)}</div></div>', unsafe_allow_html=True)
st.caption(f"Ultimo aggiornamento: {s.get('last_update','-')}. Lettura live ticker per ticker con cache 15 minuti.")
st.markdown('<div class="section-title">Scanner tecnico SMA200W / LinReg W</div>', unsafe_allow_html=True)
st.markdown('<div class="institutional-grid">'+''.join(card(r,i) for i,r in enumerate(records,1))+'</div>', unsafe_allow_html=True) if records else st.warning('Nessun dato disponibile.')
errors=[r for r in records if str(r.get('error') or '').strip()]
if errors:
    with st.expander(f"Titoli con dati tecnici incompleti ({len(errors)})", expanded=False):
        for r in errors: st.write(f"{r.get('ticker','-')}: {r.get('error')}")
