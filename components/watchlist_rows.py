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
# RENDER RIGHE STREAMLIT NATIVE
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
    zone_note = "Zona SMA200W" if in_zone else "Monitoraggio"

    row_kind = "zone" if in_zone else "normal"
    row_key = "tv_" + row_kind + "_row_" + slug_safe(current) + "_" + slug_safe(symbol)

    with st.container(key=row_key):
        row_col_1, row_col_2, row_col_3, row_col_4, row_col_5, row_col_6 = st.columns(
            [1.40, 1.00, 1.05, 1.18, 0.82, 1.55],
            vertical_alignment="center",
        )

        with row_col_1:
            st.markdown(
                '<div class="tv-cell-label">Ticker</div>'
                f'<div class="tv-cell-value tv-symbol-value">{escape(symbol)}</div>'
                f'<div class="tv-symbol-note-inline">{zone_note}</div>',
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


def render_watchlist_rows(current, symbols):
    for symbol in list(symbols):
        metrics = get_stock_metrics(symbol)
        render_row_streamlit(symbol, metrics, current)
