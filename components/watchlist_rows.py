from html import escape

import streamlit as st

from utils.symbols import slug_safe, url_tradingview
from utils.formatting import (
    formatta_prezzo,
    formatta_percentuale,
    classe_percentuale,
    classe_zona_sma,
    cell_html,
)
from utils.market_data import (
    get_stock_metrics,
    is_in_sma200_zone,
)
from utils.watchlist_storage import salva_sessione_su_disco


# =========================
# CSS VISTA COMPATTA
# =========================

def render_compact_rows_css():
    st.markdown(
        """
<style>
div[class*="st-key-tv_compact_normal_row_"],
div[class*="st-key-tv_compact_zone_row_"] {
    position: relative;
    margin: 0.28rem 0;
    border-radius: 11px;
    overflow: hidden;
}

div[class*="st-key-tv_compact_normal_row_"] {
    border: 1px solid rgba(48, 54, 61, 0.72);
    background: rgba(13, 17, 23, 0.34);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
}

div[class*="st-key-tv_compact_normal_row_"]:hover {
    border-color: rgba(0, 176, 255, 0.55);
    background: rgba(22, 27, 34, 0.68);
}

div[class*="st-key-tv_compact_zone_row_"] {
    border: 1px solid rgba(255, 140, 0, 0.82);
    background:
        radial-gradient(circle at top right, rgba(255, 140, 0, 0.20), transparent 34%),
        linear-gradient(135deg, rgba(255, 140, 0, 0.15) 0%, rgba(255, 179, 71, 0.07) 100%);
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.04),
        0 0 15px rgba(255, 140, 0, 0.28);
}

div[class*="st-key-tv_compact_zone_row_"]:hover {
    border-color: rgba(255, 179, 71, 0.98);
    background:
        radial-gradient(circle at top right, rgba(255, 140, 0, 0.25), transparent 34%),
        linear-gradient(135deg, rgba(255, 140, 0, 0.22) 0%, rgba(255, 179, 71, 0.10) 100%);
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.05),
        0 0 18px rgba(255, 140, 0, 0.42);
}

.tv-compact-row-link {
    display: block;
    width: 100%;
    color: inherit !important;
    text-decoration: none !important;
    cursor: pointer;
}

.tv-compact-row-link:hover {
    color: inherit !important;
    text-decoration: none !important;
}

/* Rende cliccabile tutta la card compatta, anche le zone vuote a destra/sinistra. */
.tv-compact-row-link::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: 8;
}

.tv-compact-row-inner {
    position: relative;
    z-index: 2;
    pointer-events: none;
    width: 100%;
    box-sizing: border-box;
    padding: 0.42rem 0.58rem;
}

.tv-compact-row-line-1,
.tv-compact-row-line-2 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.62rem;
    min-width: 0;
}

.tv-compact-row-line-1 {
    margin-bottom: 0.16rem;
}

.tv-compact-title {
    min-width: 0;
    display: flex;
    align-items: baseline;
    overflow: hidden;
}

.tv-compact-symbol {
    color: #e6edf3;
    font-size: 0.92rem;
    font-weight: 950;
    letter-spacing: -0.02em;
    white-space: nowrap;
}

.tv-compact-separator {
    color: #5f7899;
    font-size: 0.72rem;
    font-weight: 900;
    margin: 0 0.36rem;
    white-space: nowrap;
}

.tv-compact-name {
    color: #9fb3d1;
    font-size: 0.74rem;
    font-weight: 750;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 360px;
}

/* Stile usato SOLO nella vista non compatta per ticker + nome titolo. */
.tv-desktop-symbol-line {
    display: flex;
    align-items: baseline;
    min-width: 0;
    overflow: hidden;
}

.tv-desktop-symbol-main {
    white-space: nowrap;
    flex-shrink: 0;
}

.tv-desktop-symbol-name {
    color: #9fb3d1;
    font-size: 0.78rem;
    font-weight: 750;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.tv-compact-price-block {
    display: flex;
    align-items: baseline;
    gap: 0.52rem;
    flex-shrink: 0;
    white-space: nowrap;
}

.tv-compact-price {
    color: #e6edf3;
    font-size: 0.82rem;
    font-weight: 850;
}

.tv-compact-meta-left {
    min-width: 0;
    display: flex;
    align-items: baseline;
    overflow: hidden;
}

.tv-compact-meta,
.tv-compact-dist {
    font-size: 0.72rem;
    font-weight: 850;
    white-space: nowrap;
}

.tv-compact-meta {
    color: #9fb3d1;
}

.tv-compact-row-line-2 {
    font-size: 0.72rem;
    font-weight: 850;
}

@media (max-width: 640px) {
    .tv-compact-row-inner {
        padding: 0.40rem 0.50rem;
    }

    .tv-compact-row-line-1,
    .tv-compact-row-line-2 {
        gap: 0.42rem;
    }

    .tv-compact-symbol {
        font-size: 0.86rem;
    }

    .tv-compact-name {
        font-size: 0.68rem;
        max-width: 118px;
    }

    .tv-compact-separator {
        margin: 0 0.24rem;
        font-size: 0.64rem;
    }

    .tv-compact-price-block {
        gap: 0.34rem;
    }

    .tv-compact-price {
        font-size: 0.74rem;
    }

    .tv-compact-meta,
    .tv-compact-dist,
    .tv-compact-row-line-2 {
        font-size: 0.64rem;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )


# =========================
# DATI ANAGRAFICI TITOLO
# =========================

@st.cache_data(ttl=86400, show_spinner=False)
def get_company_name_from_yfinance(symbol):
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.get_info()
        return (
            info.get("shortName")
            or info.get("longName")
            or info.get("displayName")
            or ""
        )
    except Exception:
        return ""


def get_company_name(symbol, metrics):
    company_name = (
        metrics.get("name")
        or metrics.get("short_name")
        or metrics.get("shortName")
        or metrics.get("long_name")
        or metrics.get("longName")
        or metrics.get("company_name")
        or metrics.get("companyName")
        or ""
    )

    if not company_name:
        company_name = get_company_name_from_yfinance(symbol)

    if str(company_name).strip().upper() == str(symbol).strip().upper():
        return ""

    return str(company_name or "").strip()


# =========================
# ORDINAMENTO SIMBOLI
# =========================

def sposta_elemento(lista, elemento, direzione):
    lista_nuova = list(lista)

    if elemento not in lista_nuova:
        return lista_nuova

    indice = lista_nuova.index(elemento)
    nuovo_indice = indice + direzione

    if nuovo_indice < 0 or nuovo_indice >= len(lista_nuova):
        return lista_nuova

    lista_nuova[indice], lista_nuova[nuovo_indice] = (
        lista_nuova[nuovo_indice],
        lista_nuova[indice],
    )

    return lista_nuova


def sposta_simbolo(nome_lista, simbolo, direzione):
    data = st.session_state["tv_watchlists_data"]
    simboli = data["watchlists"].get(nome_lista, [])
    nuovi_simboli = sposta_elemento(simboli, simbolo, direzione)

    if nuovi_simboli == simboli:
        return

    data["watchlists"][nome_lista] = nuovi_simboli
    salva_sessione_su_disco()


# =========================
# ORDINAMENTO VISTA COMPATTA
# =========================

def sort_rows_for_compact(rows):
    """
    Ordina SOLO la vista compatta per vicinanza alla SMA200W.

    Criterio:
    - distanza disponibile: prima, ordinata per abs(dist_pct) crescente
    - distanza mancante: in fondo

    Non modifica l'ordine salvato della watchlist.
    """
    def sort_key(item):
        symbol, metrics = item
        dist_pct = metrics.get("dist_pct")

        if dist_pct is None:
            return (1, float("inf"), str(symbol))

        return (0, abs(dist_pct), str(symbol))

    return sorted(rows, key=sort_key)


# =========================
# RENDER RIGHE DESKTOP
# =========================

def render_row_streamlit(symbol, metrics, current):
    dist_pct = metrics["dist_pct"]
    daily_pct = metrics["daily_change_pct"]
    sma200w = metrics.get("sma200w")

    prezzo = formatta_prezzo(metrics["last_price"], metrics["currency"])
    sma200w_testo = formatta_prezzo(sma200w, metrics["currency"])
    distanza = formatta_percentuale(dist_pct)
    daily = formatta_percentuale(daily_pct)

    daily_class = classe_percentuale(daily_pct)
    dist_class = classe_zona_sma(dist_pct)
    in_zone = is_in_sma200_zone(dist_pct)
    zone_note = "Zona SMA200W" if in_zone else ""

    row_kind = "zone" if in_zone else "normal"
    row_key = "tv_" + row_kind + "_row_" + slug_safe(current) + "_" + slug_safe(symbol)

    with st.container(key=row_key):
        row_col_1, row_col_2, row_col_3, row_col_4, row_col_5, row_col_6 = st.columns(
            [1.40, 1.00, 1.05, 1.18, 0.82, 1.55],
            vertical_alignment="center",
        )

        with row_col_1:
            company_name = get_company_name(symbol, metrics)

            company_name_html = ""
            if company_name:
                company_name_html = (
                    '<span class="tv-compact-separator">•</span>'
                    f'<span class="tv-desktop-symbol-name">{escape(company_name)}</span>'
                )

            zone_note_html = ""
            if zone_note:
                zone_note_html = f'<div class="tv-symbol-note-inline">{escape(zone_note)}</div>'

            st.markdown(
                '<div class="tv-cell-value tv-symbol-value tv-desktop-symbol-line">'
                f'<span class="tv-desktop-symbol-main">{escape(symbol)}</span>'
                f'{company_name_html}'
                '</div>'
                f'{zone_note_html}',
                unsafe_allow_html=True,
            )

        with row_col_2:
            st.markdown(cell_html("Prezzo", prezzo), unsafe_allow_html=True)

        with row_col_3:
            st.markdown(cell_html("SMA 200W", sma200w_testo), unsafe_allow_html=True)

        with row_col_4:
            st.markdown(cell_html("Distanza SMA200W", distanza, dist_class), unsafe_allow_html=True)

        with row_col_5:
            st.markdown(cell_html("Daily", daily, daily_class), unsafe_allow_html=True)

        with row_col_6:
            st.markdown('<div class="tv-cell-label">Azioni</div>', unsafe_allow_html=True)
            action_col_0, action_col_1, action_col_2, action_col_3, action_col_4 = st.columns(5)

            with action_col_0:
                st.link_button(
                    "📊",
                    url_tradingview(symbol),
                    use_container_width=True,
                    help="Apri TradingView esterno",
                )

            with action_col_1:
                if st.button(
                    "📈",
                    key="tv_graph_" + symbol + "_" + current,
                    use_container_width=True,
                    help="Apri grafico tecnico weekly",
                ):
                    st.session_state["ticker_selezionato"] = symbol
                    st.switch_page("pages/grafico.py")

            with action_col_2:
                if st.button(
                    "▲",
                    key="tv_up_" + symbol + "_" + current,
                    use_container_width=True,
                    help="Sposta simbolo in alto",
                ):
                    sposta_simbolo(current, symbol, -1)
                    st.rerun()

            with action_col_3:
                if st.button(
                    "▼",
                    key="tv_down_" + symbol + "_" + current,
                    use_container_width=True,
                    help="Sposta simbolo in basso",
                ):
                    sposta_simbolo(current, symbol, 1)
                    st.rerun()

            with action_col_4:
                if st.button(
                    "×",
                    key="tv_delete_" + symbol + "_" + current,
                    use_container_width=True,
                    help="Elimina simbolo dalla watchlist",
                ):
                    if symbol in st.session_state["tv_watchlists_data"]["watchlists"][current]:
                        st.session_state["tv_watchlists_data"]["watchlists"][current].remove(symbol)
                        salva_sessione_su_disco()
                        st.cache_data.clear()
                        st.rerun()


# =========================
# RENDER RIGHE COMPATTE MOBILE
# =========================

def render_row_compact(symbol, metrics, current):
    dist_pct = metrics["dist_pct"]
    daily_pct = metrics["daily_change_pct"]
    sma200w = metrics.get("sma200w")

    prezzo = formatta_prezzo(metrics["last_price"], metrics["currency"])
    sma200w_testo = formatta_prezzo(sma200w, metrics["currency"])
    distanza = formatta_percentuale(dist_pct)
    daily = formatta_percentuale(daily_pct)

    daily_class = classe_percentuale(daily_pct)
    dist_class = classe_zona_sma(dist_pct)

    in_zone = is_in_sma200_zone(dist_pct)
    row_kind = "zone" if in_zone else "normal"
    row_key = "tv_compact_" + row_kind + "_row_" + slug_safe(current) + "_" + slug_safe(symbol)

    company_name = get_company_name(symbol, metrics)
    tv_url = url_tradingview(symbol)

    company_name_html = ""
    if company_name:
        company_name_html = (
            '<span class="tv-compact-separator">•</span>'
            f'<span class="tv-compact-name">{escape(company_name)}</span>'
        )

    dist_html = (
        '<span class="tv-compact-separator">•</span>'
        f'<span class="tv-compact-dist {dist_class}">Dist {escape(distanza)}</span>'
    )

    price_separator_html = '<span class="tv-compact-separator">•</span>'

    html = (
        f'<a class="tv-compact-row-link" href="{escape(tv_url, quote=True)}" target="_blank" rel="noopener noreferrer">'
        '<div class="tv-compact-row-inner">'
        '<div class="tv-compact-row-line-1">'
        '<div class="tv-compact-title">'
        f'<span class="tv-compact-symbol">{escape(symbol)}</span>'
        f'{company_name_html}'
        '</div>'
        '<div class="tv-compact-price-block">'
        f'<span class="tv-compact-price">{escape(prezzo)}</span>'
        f'{price_separator_html}'
        f'<span class="{daily_class}">{escape(daily)}</span>'
        '</div>'
        '</div>'
        '<div class="tv-compact-row-line-2">'
        '<div class="tv-compact-meta-left">'
        f'<span class="tv-compact-meta">SMA200W {escape(sma200w_testo)}</span>'
        f'{dist_html}'
        '</div>'
        '</div>'
        '</div>'
        '</a>'
    )

    with st.container(key=row_key):
        st.markdown(html, unsafe_allow_html=True)


# =========================
# ENTRY POINT RIGHE
# =========================

def render_watchlist_rows(current, symbols):
    render_compact_rows_css()

    compact_mode = bool(st.session_state.get("tv_compact_rows", False))

    rows = []

    for symbol in list(symbols):
        metrics = get_stock_metrics(symbol)
        rows.append((symbol, metrics))

    if compact_mode:
        rows = sort_rows_for_compact(rows)

    for symbol, metrics in rows:
        if compact_mode:
            render_row_compact(symbol, metrics, current)
        else:
            render_row_streamlit(symbol, metrics, current)
