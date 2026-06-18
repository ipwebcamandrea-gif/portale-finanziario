from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ticker_lookup_selector import render_ticker_lookup_selector
from utils.auth import require_login
from utils.portfolio_calculations import enrich_portfolio_df
from utils.portfolio_formatting import fmt_eur, fmt_num, fmt_pct
from utils.portfolio_prices import fetch_last_quote
from utils.portfolio_storage import load_portfolio
from utils.portfolio_tradingview import build_tradingview_symbol
from utils.symbols import url_tradingview
from utils.target_calculations import build_simulation_scenarios, build_target_scenarios, pct_change, safe_float
from utils.target_data import fetch_yfinance_targets, now_iso
from utils.target_storage import get_saved_target, load_targets, upsert_target


require_login()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "portfolio" / "portafoglio.json"
TARGET_PATH = BASE_DIR / "portfolio" / "target_analisti.json"
GLOBAL_CSS_PATH = BASE_DIR / "css" / "global.css"
CSS_PATH = BASE_DIR / "css" / "target_analisti.css"

st.set_page_config(page_title="Target Analisti", page_icon="🎯", layout="wide", initial_sidebar_state="collapsed")


def load_css() -> None:
    for css_path in (GLOBAL_CSS_PATH, CSS_PATH):
        if css_path.exists():
            st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def fmt_money(value, currency: str) -> str:
    value = safe_float(value)
    if value is None:
        return "N/D"
    return f"{fmt_eur(value)} {str(currency or '').upper()}".strip()


def fmt_eur_result(result: dict) -> str:
    if result and result.get("ok"):
        return f"≈ {fmt_eur(result.get('value'))} EUR"
    return "EUR non disponibile"


def value_class(value) -> str:
    value = safe_float(value, 0.0)
    if value > 0:
        return "target-positive"
    if value < 0:
        return "target-negative"
    return "target-neutral"


def forecast_url(tv_symbol: str, yf_symbol: str) -> str:
    if tv_symbol:
        return f"https://www.tradingview.com/symbols/{tv_symbol.replace(':', '-')}/forecast/"
    try:
        tv_url = url_tradingview(yf_symbol)
        return tv_url.rstrip("/") + "/forecast/"
    except Exception:
        return "https://www.tradingview.com/"


def set_target_selection(*, yf_symbol: str, ticker: str = "", tv_symbol: str = "", name: str = "", market: str = "", currency: str = "", source: str = "") -> None:
    st.session_state["target_selected"] = {
        "yf_symbol": str(yf_symbol or "").strip().upper(),
        "ticker": str(ticker or "").strip().upper(),
        "tv_symbol": str(tv_symbol or "").strip().upper(),
        "name": str(name or "").strip(),
        "market": str(market or "").strip().upper(),
        "currency": str(currency or "").strip().upper(),
        "source": source,
    }


def get_selection_from_state() -> dict:
    selected = st.session_state.get("target_selected")
    if isinstance(selected, dict) and selected.get("yf_symbol"):
        return selected
    # Compatibility with simple keys set by old/new buttons.
    yf_symbol = st.session_state.get("target_yf_symbol") or st.session_state.get("ticker_selezionato") or ""
    if yf_symbol:
        return {
            "yf_symbol": str(yf_symbol).strip().upper(),
            "ticker": str(st.session_state.get("target_ticker") or yf_symbol).strip().upper(),
            "tv_symbol": str(st.session_state.get("target_tv_symbol") or "").strip().upper(),
            "name": str(st.session_state.get("target_name") or "").strip(),
            "market": str(st.session_state.get("target_market") or "").strip().upper(),
            "currency": str(st.session_state.get("target_currency") or "").strip().upper(),
            "source": str(st.session_state.get("target_source") or ""),
        }
    return {}


def portfolio_rows_for_symbol(yf_symbol: str) -> pd.DataFrame:
    df = load_portfolio(DATA_PATH)
    df = enrich_portfolio_df(df)
    if df.empty:
        return df
    clean = str(yf_symbol or "").strip().upper()
    mask = df["yf_symbol"].astype(str).str.upper().eq(clean) if "yf_symbol" in df.columns else False
    if not mask.any() and "ticker" in df.columns:
        mask = df["ticker"].astype(str).str.upper().eq(clean.replace(".MI", ""))
    return df.loc[mask]


def render_header(selection: dict, target_data: dict | None) -> None:
    yf_symbol = selection.get("yf_symbol", "")
    title_name = (target_data or {}).get("name") or selection.get("name") or yf_symbol
    currency = (target_data or {}).get("currency") or selection.get("currency") or ""
    market = (target_data or {}).get("market") or selection.get("market") or ""
    st.markdown(f'<div class="target-page-title">🎯 Target Analisti — {yf_symbol or "Seleziona titolo"}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="target-page-subtitle">{title_name} · {market or "Mercato N/D"} · {currency or "Valuta N/D"}</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.05, 1.35, 4.0])
    with c1:
        if st.button("← Cockpit", key="target_back_cockpit", use_container_width=True):
            st.switch_page("pages/dashboard.py")
    with c2:
        tv_symbol = (target_data or {}).get("tv_symbol") or selection.get("tv_symbol", "")
        st.link_button("Apri TradingView 🎯", forecast_url(tv_symbol, yf_symbol), use_container_width=True)


def fetch_and_save(selection: dict) -> dict | None:
    yf_symbol = selection.get("yf_symbol", "")
    result = fetch_yfinance_targets(
        yf_symbol,
        ticker=selection.get("ticker", ""),
        market=selection.get("market", ""),
        currency=selection.get("currency", ""),
        tv_symbol=selection.get("tv_symbol", ""),
    )
    if result.get("ok"):
        saved = upsert_target(TARGET_PATH, yf_symbol, result)
        st.success("Target aggiornati da yfinance e salvati.")
        return saved
    st.warning(result.get("error", "Target automatici non disponibili."))
    return None


def load_effective_target(selection: dict) -> tuple[dict | None, str]:
    yf_symbol = selection.get("yf_symbol", "")
    saved = get_saved_target(TARGET_PATH, yf_symbol) if yf_symbol else None
    if saved:
        # Always refresh current price from quote if possible, without overwriting saved targets.
        quote = fetch_last_quote(yf_symbol)
        if quote.get("ok"):
            saved = {**saved, "current_price": quote.get("last")}
        return saved, "saved"
    return None, "none"


def render_status(target_data: dict | None, mode: str) -> None:
    if not target_data:
        st.markdown('<div class="target-warning-box">Nessun target salvato per questo titolo. Prova con “Aggiorna target da yfinance” oppure inserisci i valori manualmente.</div>', unsafe_allow_html=True)
        return
    updated = target_data.get("updated_at", "")
    source = target_data.get("source", mode)
    analysts = target_data.get("analyst_count") or "N/D"
    rating = target_data.get("rating") or "N/D"
    st.markdown(f'<div class="target-status-pill">Fonte: {source} · Aggiornato: {updated or "N/D"} · Analisti: {analysts} · Rating: {rating}</div>', unsafe_allow_html=True)


def render_target_cards(target_data: dict) -> None:
    currency = target_data.get("currency", "")
    current = safe_float(target_data.get("current_price"))
    cols = st.columns(4)
    items = [
        ("Prezzo attuale", current, None),
        ("Target minimo", target_data.get("target_low"), pct_change(target_data.get("target_low"), current)),
        ("Target medio", target_data.get("target_mean"), pct_change(target_data.get("target_mean"), current)),
        ("Target massimo", target_data.get("target_high"), pct_change(target_data.get("target_high"), current)),
    ]
    for col, (label, value, pct) in zip(cols, items):
        with col:
            pct_html = "" if pct is None else f'<div class="target-card-subtitle {value_class(pct)}">{fmt_pct(pct)}</div>'
            st.markdown(
                '<div class="target-card">'
                f'<div class="target-card-label">{label}</div>'
                f'<div class="target-card-value">{fmt_money(value, currency)}</div>'
                f'{pct_html}'
                '</div>',
                unsafe_allow_html=True,
            )


def render_chart(target_data: dict) -> None:
    currency = target_data.get("currency", "")
    labels = ["Prezzo attuale", "Target minimo", "Target medio", "Target massimo"]
    values = [safe_float(target_data.get("current_price")), safe_float(target_data.get("target_low")), safe_float(target_data.get("target_mean")), safe_float(target_data.get("target_high"))]
    filtered = [(l, v) for l, v in zip(labels, values) if v is not None]
    if not filtered:
        return
    fig = go.Figure(go.Bar(x=[x[0] for x in filtered], y=[x[1] for x in filtered], text=[fmt_money(x[1], currency) for x in filtered], textposition="auto"))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10), plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font=dict(color="#e6edf3"), showlegend=False)
    fig.update_yaxes(title_text=currency or "Prezzo", gridcolor="rgba(255,255,255,0.08)")
    st.plotly_chart(fig, use_container_width=True)


def render_scenario_rows(title: str, scenarios: list[dict], currency: str, *, gain_key: str = "gain_current") -> None:
    st.markdown(f'<div class="target-section-title">{title}</div>', unsafe_allow_html=True)
    for item in scenarios:
        gain = item.get(gain_key)
        gain_eur = item.get(gain_key + "_eur") or item.get("gain_eur") or {}
        subtitle = f"Target {fmt_money(item.get('target'), currency)} · Upside {fmt_pct(item.get('upside_pct')) if item.get('upside_pct') is not None else 'N/D'}"
        values = [
            f"Valore futuro: {fmt_money(item.get('future_value'), currency)}",
            f"Guadagno: <span class='{value_class(gain)}'>{fmt_money(gain, currency)}</span>",
            fmt_eur_result(gain_eur),
        ]
        st.markdown(
            '<div class="target-scenario-row">'
            f'<div><div class="target-scenario-title">{item.get("label")}</div><div class="target-scenario-note">{subtitle}</div></div>'
            f'<div class="target-scenario-values">{"<br>".join(values)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )


def render_real_position(target_data: dict, selection: dict) -> None:
    rows = portfolio_rows_for_symbol(selection.get("yf_symbol", ""))
    if rows.empty:
        return
    row = rows.iloc[0]
    qty = safe_float(row.get("quantita"), 0.0) or 0.0
    avg_price = safe_float(row.get("prezzo_medio"))
    currency = target_data.get("currency") or row.get("valuta", "")
    current = safe_float(target_data.get("current_price")) or safe_float(row.get("prezzo_mercato"))
    st.markdown('<div class="target-section-title">La tua posizione reale</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Quantità", fmt_num(qty, 2))
    c2.metric("Prezzo medio", fmt_money(avg_price, currency))
    c3.metric("Valore attuale", fmt_money(qty * current if current else None, currency))
    scenarios = build_target_scenarios({**target_data, "current_price": current, "currency": currency}, quantity=qty, avg_price=avg_price)
    render_scenario_rows("Scenari sulla posizione reale — guadagno da oggi", scenarios, currency, gain_key="gain_current")
    render_scenario_rows("Scenari sulla posizione reale — guadagno da prezzo medio", scenarios, currency, gain_key="gain_from_cost")


def render_simulation(target_data: dict) -> None:
    st.markdown('<div class="target-section-title">Simulazione investimento</div>', unsafe_allow_html=True)
    budget = st.slider("Investimento simulato", min_value=1000, max_value=100000, value=10000, step=1000, format="%d €")
    simulation = build_simulation_scenarios(target_data, budget)
    currency = target_data.get("currency", "")
    if not simulation.get("ok"):
        st.warning(simulation.get("error", "Simulazione non disponibile."))
        return
    st.caption(f"Budget {fmt_eur(budget)} EUR · Quantità teorica: {fmt_num(simulation.get('quantity'), 4)} azioni")
    render_scenario_rows("Scenari su investimento simulato", simulation.get("scenarios", []), currency, gain_key="gain_current")


def render_manual_editor(selection: dict, current_data: dict | None) -> None:
    with st.expander("Modifica manualmente target", expanded=False):
        st.caption("Fallback manuale: usa questi campi solo se yfinance non espone i target. I valori vengono salvati nel JSON target_analisti.")
        currency_default = (current_data or {}).get("currency") or selection.get("currency") or "USD"
        c1, c2, c3 = st.columns(3)
        with c1:
            low = st.number_input("Target minimo", value=float((current_data or {}).get("target_low") or 0.0), min_value=0.0, step=1.0)
        with c2:
            mean = st.number_input("Target medio", value=float((current_data or {}).get("target_mean") or 0.0), min_value=0.0, step=1.0)
        with c3:
            high = st.number_input("Target massimo", value=float((current_data or {}).get("target_high") or 0.0), min_value=0.0, step=1.0)
        analyst_count = st.number_input("Numero analisti", value=int((current_data or {}).get("analyst_count") or 0), min_value=0, step=1)
        rating = st.text_input("Rating", value=str((current_data or {}).get("rating") or ""))
        if st.button("Salva target manuali", use_container_width=True):
            data = {
                **(current_data or {}),
                "source": "manuale",
                "yf_symbol": selection.get("yf_symbol"),
                "ticker": selection.get("ticker") or selection.get("yf_symbol"),
                "tv_symbol": selection.get("tv_symbol") or build_tradingview_symbol(selection.get("market") or "NASDAQ", selection.get("ticker") or selection.get("yf_symbol"), "", currency_default),
                "name": (current_data or {}).get("name") or selection.get("name") or selection.get("yf_symbol"),
                "market": selection.get("market") or (current_data or {}).get("market") or "",
                "currency": currency_default,
                "current_price": (current_data or {}).get("current_price"),
                "target_low": low or None,
                "target_mean": mean or None,
                "target_high": high or None,
                "analyst_count": analyst_count or None,
                "rating": rating,
                "updated_at": now_iso(),
            }
            upsert_target(TARGET_PATH, selection.get("yf_symbol", ""), data)
            st.success("Target manuali salvati.")
            st.rerun()


def render_direct_selector() -> dict:
    st.info("Seleziona un titolo oppure apri questa pagina dal pulsante 🎯 di Watchlist/Portafoglio.")
    candidate = render_ticker_lookup_selector(key_prefix="target_direct")
    if candidate and st.button("Apri target selezionato", use_container_width=True):
        set_target_selection(
            yf_symbol=candidate.get("yf_symbol", ""),
            ticker=candidate.get("ticker", ""),
            tv_symbol=candidate.get("tv_symbol", ""),
            name=candidate.get("name", ""),
            market=candidate.get("market", ""),
            currency=candidate.get("currency", ""),
            source="direct",
        )
        st.rerun()
    return {}


def main() -> None:
    load_css()
    selection = get_selection_from_state()
    if not selection.get("yf_symbol"):
        st.markdown('<div class="target-page-title">🎯 Target Analisti</div>', unsafe_allow_html=True)
        render_direct_selector()
        return

    target_data, mode = load_effective_target(selection)
    render_header(selection, target_data)

    if st.button("🔄 Aggiorna target da yfinance", key="target_refresh_yfinance", use_container_width=True):
        target_data = fetch_and_save(selection) or target_data

    render_status(target_data, mode)
    if target_data:
        render_target_cards(target_data)
        render_chart(target_data)
        render_real_position(target_data, selection)
        render_simulation(target_data)
    render_manual_editor(selection, target_data)

    storage_mode = st.session_state.get("target_storage_mode", "locale")
    last_error = st.session_state.get("target_last_github_error", "")
    if storage_mode == "github":
        st.caption("Target salvati su GitHub branch data-watchlists · portfolio/target_analisti.json")
    elif storage_mode == "locale_fallback":
        st.warning("GitHub non disponibile per target_analisti.json: salvataggio locale. " + last_error)


if __name__ == "__main__":
    main()
