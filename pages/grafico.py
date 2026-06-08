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
            css = file.read()
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


local_css(GLOBAL_CSS)
local_css(GRAFICO_CSS)


# =========================
# FUNZIONI DATI
# =========================

def normalizza_dataframe_yfinance(data):
    if isinstance(data.columns, pd.MultiIndex):
        livelli_0 = list(data.columns.get_level_values(0))
        livelli_1 = list(data.columns.get_level_values(1))

        if "Close" in livelli_0:
            data.columns = data.columns.get_level_values(0)
        elif "Close" in livelli_1:
            data.columns = data.columns.get_level_values(1)
        else:
            data.columns = [
                "_".join([str(elemento) for elemento in colonna if str(elemento) != ""])
                for colonna in data.columns
            ]

    return data


@st.cache_data(ttl=900, show_spinner=False)
def scarica_dati_weekly(ticker):
    try:
        data = yf.download(
            ticker,
            period="10y",
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


# =========================
# GRAFICO
# =========================

def crea_grafico_weekly(data, ticker):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        row_heights=[0.78, 0.22],
        subplot_titles=(f"{ticker} - Weekly 10 anni", "Volume weekly")
    )

    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name=ticker,
            increasing_line_color="#00c087",
            decreasing_line_color="#ff4d4d",
            increasing_fillcolor="#00c087",
            decreasing_fillcolor="#ff4d4d"
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
            line=dict(color="#26a69a", width=2.0)
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
            line=dict(color="#2962ff", width=2.2)
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
            line=dict(color="#ffeb3b", width=2.1)
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
            line=dict(color="#ff9800", width=2.3)
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
                opacity=0.42,
                marker_color="#5f6b7a"
            ),
            row=2,
            col=1
        )

    fig.update_layout(
        template="plotly_dark",
        height=820,
        margin=dict(l=10, r=55, t=60, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.035,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117"
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.06)",
        zeroline=False
    )

    fig.update_yaxes(
        title_text="Prezzo",
        row=1,
        col=1,
        side="right",
        showgrid=True,
        gridcolor="rgba(255,255,255,0.06)",
        zeroline=False
    )

    fig.update_yaxes(
        title_text="Volume",
        row=2,
        col=1,
        side="right",
        showgrid=True,
        gridcolor="rgba(255,255,255,0.05)",
        zeroline=False
    )

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


st.markdown(
    f"""
    <div class="grafico-header">
        <div class="grafico-title">Analisi Weekly: {ticker}</div>
        <div class="grafico-subtitle">
            Vista a 10 anni su timeframe weekly con WMA 21W, WMA 50W,
            WMA 200W, EMA 200W e SMA 200W.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# NAVIGAZIONE
# =========================

col_back, col_info = st.columns([1.2, 4.8])

with col_back:
    if st.button("⬅️ Torna al Cockpit"):
        st.switch_page("pages/dashboard.py")

with col_info:
    st.info("Timeframe weekly · Periodo fisso 10 anni · Medie mobili weekly")


# =========================
# DOWNLOAD DATI
# =========================

with st.spinner(f"Caricamento dati weekly a 10 anni per {ticker}..."):
    data, errore_download = scarica_dati_weekly(ticker)

if errore_download:
    st.warning(
        "Yahoo Finance/YFinance ha limitato o interrotto temporaneamente la richiesta. "
        "Riprova tra qualche minuto."
    )

if data.empty:
    st.error(
        f"Non sono stati trovati dati validi per il ticker {ticker}. "
        "Controlla il simbolo nella Watchlist."
    )

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
    st.metric(
        "Prezzo attuale",
        formatta_numero(metriche["prezzo"])
    )

with kpi_2:
    st.metric(
        "SMA 200W",
        formatta_numero(metriche["sma_200w"])
    )

with kpi_3:
    st.metric(
        "Distanza SMA 200W",
        formatta_percentuale(metriche["distanza_sma_200w"])
    )

with kpi_4:
    st.metric(
        "Rendimento 52W",
        formatta_percentuale(metriche["rendimento_52w"])
    )


kpi_5, kpi_6, kpi_7, kpi_8 = st.columns(4)

with kpi_5:
    st.metric(
        "WMA 21W",
        formatta_numero(metriche["wma_21w"])
    )

with kpi_6:
    st.metric(
        "WMA 50W",
        formatta_numero(metriche["wma_50w"])
    )

with kpi_7:
    st.metric(
        "WMA 200W",
        formatta_numero(metriche["wma_200w"])
    )

with kpi_8:
    st.metric(
        "EMA 200W",
        formatta_numero(metriche["ema_200w"])
    )


# =========================
# GRAFICO
# =========================

st.subheader("Grafico tecnico weekly")

fig = crea_grafico_weekly(data, ticker)
st.plotly_chart(fig, use_container_width=True)


# =========================
# EXPORT DATI
# =========================

csv_data = data.to_csv(index=True).encode("utf-8")

st.download_button(
    label="⬇️ Scarica dati weekly CSV",
    data=csv_data,
    file_name=f"{ticker}_weekly_10y.csv",
    mime="text/csv"
)
