import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pathlib import Path
from plotly.subplots import make_subplots


# =========================
# PROTEZIONE LOGIN
# =========================

if not st.session_state.get("authenticated", False):
    st.error("Accesso negato.")

    if st.button("Torna al Login"):
        st.switch_page("main.py")

    st.stop()


# =========================
# CONFIGURAZIONE FILE / CSS
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent

GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
GRAFICO_CSS = ROOT_DIR / "css" / "grafico.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown(
                f"<style>{file.read()}</style>",
                unsafe_allow_html=True
            )


local_css(GLOBAL_CSS)
local_css(GRAFICO_CSS)


# =========================
# FUNZIONI DATI
# =========================

def normalizza_dataframe_yfinance(data):
    if isinstance(data.columns, pd.MultiIndex):
        level_0 = list(data.columns.get_level_values(0))
        level_1 = list(data.columns.get_level_values(1))

        if "Close" in level_0:
            data.columns = data.columns.get_level_values(0)
        elif "Close" in level_1:
            data.columns = data.columns.get_level_values(1)
        else:
            data.columns = [
                "_".join([str(x) for x in col if str(x) != ""])
                for col in data.columns
            ]

    return data


@st.cache_data(ttl=900, show_spinner=False)
def scarica_dati_weekly(ticker):
    try:
        data = yf.download(
            ticker,
            period="5y",
            interval="1wk",
            progress=False,
            auto_adjust=False,
            threads=False
        )
    except Exception as errore:
        return pd.DataFrame(), str(errore)

    if data is None or data.empty:
        return pd.DataFrame(), None

    data = normalizza_dataframe_yfinance(data)

    colonne_richieste = ["Open", "High", "Low", "Close"]

    for colonna in colonne_richieste:
        if colonna not in data.columns:
            return pd.DataFrame(), None

    data = data.dropna(subset=colonne_richieste)

    return data, None


def valore_float(valore):
    if isinstance(valore, pd.Series):
        valore = valore.dropna()

        if valore.empty:
            return None

        valore = valore.iloc[0]

    if pd.isna(valore):
        return None

    return float(valore)


def calcola_wma(serie, periodo):
    pesi = np.arange(1, periodo + 1)

    return serie.rolling(periodo).apply(
        lambda valori: np.dot(valori, pesi) / pesi.sum(),
        raw=True
    )


def prepara_indicatori_weekly(data):
    data_plot = data.copy()

    data_plot["WMA21W"] = calcola_wma(data_plot["Close"], 21)
    data_plot["WMA50W"] = calcola_wma(data_plot["Close"], 50)
    data_plot["WMA200W"] = calcola_wma(data_plot["Close"], 200)
    data_plot["EMA200W"] = data_plot["Close"].ewm(span=200, adjust=False).mean()
    data_plot["SMA200W"] = data_plot["Close"].rolling(200).mean()

    return data_plot


def calcola_rendimento(data, settimane):
    if data is None or data.empty:
        return None

    if len(data) <= settimane:
        return None

    prezzo_attuale = valore_float(data["Close"].iloc[-1])
    prezzo_passato = valore_float(data["Close"].iloc[-settimane])

    if prezzo_attuale is None or prezzo_passato is None:
        return None

    if prezzo_passato == 0:
        return None

    return ((prezzo_attuale - prezzo_passato) / prezzo_passato) * 100


def calcola_metriche(data):
    prezzo = valore_float(data["Close"].iloc[-1])
    max_periodo = valore_float(data["High"].max())
    min_periodo = valore_float(data["Low"].min())

    wma_21w = valore_float(data["WMA21W"].iloc[-1])
    wma_50w = valore_float(data["WMA50W"].iloc[-1])
    wma_200w = valore_float(data["WMA200W"].iloc[-1])
    ema_200w = valore_float(data["EMA200W"].iloc[-1])
    sma_200w = valore_float(data["SMA200W"].iloc[-1])

    distanza_sma_200w = None

    if prezzo is not None and sma_200w is not None and sma_200w != 0:
        distanza_sma_200w = ((prezzo - sma_200w) / sma_200w) * 100

    rendimento_13w = calcola_rendimento(data, 13)
    rendimento_26w = calcola_rendimento(data, 26)
    rendimento_52w = calcola_rendimento(data, 52)

    return {
        "prezzo": prezzo,
        "max_periodo": max_periodo,
        "min_periodo": min_periodo,
        "wma_21w": wma_21w,
        "wma_50w": wma_50w,
        "wma_200w": wma_200w,
        "ema_200w": ema_200w,
        "sma_200w": sma_200w,
        "distanza_sma_200w": distanza_sma_200w,
        "rendimento_13w": rendimento_13w,
        "rendimento_26w": rendimento_26w,
        "rendimento_52w": rendimento_52w
    }


# =========================
# FORMATTAZIONE
# =========================

def formatta_numero(valore):
    if valore is None:
        return "N/D"

    return f"{valore:.2f}"


def formatta_percentuale(valore):
    if valore is None:
        return "N/D"

    return f"{valore:.2f} %"


def classe_valore(valore):
    if valore is None:
        return "neutral"

    if valore > 0:
        return "positive"

    if valore < 0:
        return "negative"

    return "neutral"


def render_kpi_card(label, value, note="", css_class=""):
    html = (
        '<div class="grafico-kpi-card">'
        f'<div class="grafico-kpi-label">{label}</div>'
        f'<div class="grafico-kpi-value {css_class}">{value}</div>'
        f'<div class="grafico-kpi-note">{note}</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


# =========================
# GRAFICO
# =========================

def crea_grafico_weekly(data, ticker):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.76, 0.24],
        subplot_titles=(f"{ticker} - Weekly 5 anni", "Volume weekly")
    )

    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name=ticker
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["WMA21W"],
            mode="lines",
            name="WMA 21W",
            line=dict(color="#ffffff", width=1.8)
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["WMA50W"],
            mode="lines",
            name="WMA 50W",
            line=dict(color="#26a69a", width=1.9)
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["WMA200W"],
            mode="lines",
            name="WMA 200W",
            line=dict(color="#00b0ff", width=2.1)
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["EMA200W"],
            mode="lines",
            name="EMA 200W",
            line=dict(color="#f5c542", width=2.0)
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["SMA200W"],
            mode="lines",
            name="SMA 200W",
            line=dict(color="#ff9800", width=2.2)
        ),
        row=1,
        col=1
    )

    if "Volume" in data.columns:
        fig.add_trace(
            go.Bar(
                x=data.index,
                y=data["Volume"],
                name="Volume",
                opacity=0.45,
                marker_color="#5f6b7a"
            ),
            row=2,
            col=1
        )

    fig.update_layout(
        template="plotly_dark",
        height=760,
        margin=dict(l=10, r=10, t=55, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="right",
            x=1
        )
    )

    fig.update_yaxes(title_text="Prezzo", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig


# =========================
# TICKER / HEADER
# =========================

ticker = st.session_state.get("ticker_selezionato", None)

if ticker is None:
    st.warning(
        "Nessun ticker selezionato. "
        "Apri questa pagina dalla Watchlist usando il pulsante 📈."
    )

    if st.button("⬅️ Torna al Cockpit"):
        st.switch_page("pages/dashboard.py")

    st.stop()


header_html = (
    '<div class="grafico-header">'
    f'<div class="grafico-title">Analisi Weekly: {ticker}</div>'
    '<div class="grafico-subtitle">'
    'Vista unica a 5 anni su timeframe weekly con WMA 21W, WMA 50W, '
    'WMA 200W, EMA 200W e SMA 200W.'
    '</div>'
    '</div>'
)

st.markdown(header_html, unsafe_allow_html=True)


# =========================
# NAVIGAZIONE
# =========================

col_back, col_info = st.columns([1.2, 4.8])

with col_back:
    if st.button("⬅️ Torna al Cockpit"):
        st.switch_page("pages/dashboard.py")

with col_info:
    info_html = (
        '<div class="grafico-control-panel">'
        '<div class="grafico-control-title">Vista grafico</div>'
        '<div class="grafico-control-subtitle">'
        'Timeframe weekly · Periodo fisso 5 anni · Medie mobili weekly.'
        '</div>'
        '</div>'
    )

    st.markdown(info_html, unsafe_allow_html=True)


# =========================
# DOWNLOAD DATI
# =========================

with st.spinner(f"Caricamento dati weekly a 5 anni per {ticker}..."):
    data, errore_download = scarica_dati_weekly(ticker)

if errore_download:
    st.warning(
        "Yahoo Finance/YFinance ha limitato o interrotto temporaneamente la richiesta. "
        "Riprova tra qualche minuto."
    )

if data.empty:
    errore_html = (
        '<div class="grafico-status-card">'
        '<div class="grafico-status-title">Dati non disponibili</div>'
        f'<div class="grafico-status-text">'
        f'Non sono stati trovati dati validi per il ticker {ticker}. '
        'Controlla il simbolo nella Watchlist.'
        '</div>'
        '</div>'
    )

    st.markdown(errore_html, unsafe_allow_html=True)

    if st.button("⬅️ Torna al Cockpit", key="back_no_data"):
        st.switch_page("pages/dashboard.py")

    st.stop()


data = prepara_indicatori_weekly(data)


# =========================
# METRICHE
# =========================

metriche = calcola_metriche(data)

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

with kpi_1:
    render_kpi_card(
        "Prezzo attuale",
        formatta_numero(metriche["prezzo"]),
        "Ultima chiusura weekly"
    )

with kpi_2:
    render_kpi_card(
        "SMA 200W",
        formatta_numero(metriche["sma_200w"]),
        "Media mobile semplice weekly"
    )

with kpi_3:
    distanza = metriche["distanza_sma_200w"]

    render_kpi_card(
        "Distanza SMA 200W",
        formatta_percentuale(distanza),
        "Prezzo vs SMA 200W",
        classe_valore(distanza)
    )

with kpi_4:
    rendimento_52w = metriche["rendimento_52w"]

    render_kpi_card(
        "Rendimento 52W",
        formatta_percentuale(rendimento_52w),
        "Ultime 52 settimane",
        classe_valore(rendimento_52w)
    )


kpi_5, kpi_6, kpi_7, kpi_8 = st.columns(4)

with kpi_5:
    render_kpi_card(
        "WMA 21W",
        formatta_numero(metriche["wma_21w"]),
        "Linea bianca"
    )

with kpi_6:
    render_kpi_card(
        "WMA 50W",
        formatta_numero(metriche["wma_50w"]),
        "Linea verde"
    )

with kpi_7:
    render_kpi_card(
        "WMA 200W",
        formatta_numero(metriche["wma_200w"]),
        "Linea blu"
    )

with kpi_8:
    render_kpi_card(
        "EMA 200W",
        formatta_numero(metriche["ema_200w"]),
        "Linea gialla"
    )


# =========================
# GRAFICO
# =========================

chart_html = (
    '<div class="grafico-chart-card">'
    '<div class="grafico-section-title">Grafico tecnico weekly</div>'
    '<div class="grafico-section-subtitle">'
    'Candele weekly a 5 anni con WMA 21W, WMA 50W, WMA 200W, '
    'EMA 200W e SMA 200W.'
    '</div>'
    '</div>'
)

st.markdown(chart_html, unsafe_allow_html=True)

fig = crea_grafico_weekly(data, ticker)
st.plotly_chart(fig, use_container_width=True)


# =========================
# EXPORT DATI
# =========================

csv_data = data.to_csv(index=True).encode("utf-8")

st.download_button(
    label="⬇️ Scarica dati weekly CSV",
    data=csv_data,
    file_name=f"{ticker}_weekly_5y.csv",
    mime="text/csv"
)
