import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pathlib import Path
from plotly.subplots import make_subplots

# =========================
# LOGIN CHECK
# =========================

if not st.session_state.get("authenticated", False):
    st.error("Accesso negato.")
    if st.button("Torna al Login"):
        st.switch_page("main.py")
    st.stop()

# =========================
# CSS
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent
GLOBAL_CSS = ROOT_DIR / "css" / "global.css"
GRAFICO_CSS = ROOT_DIR / "css" / "grafico.css"


def local_css(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            st.markdown("<style>" + file.read() + "</style>", unsafe_allow_html=True)


local_css(GLOBAL_CSS)
local_css(GRAFICO_CSS)

# =========================
# PARAMETERS
# =========================

PERIODO_DATI = "10y"
INTERVALLO_DATI = "1wk"

WMA_21 = 21
WMA_50 = 50
WMA_200 = 200
EMA_200 = 200
SMA_200 = 200

STOCH_RSI_RSI_LENGTH = 20
STOCH_RSI_LENGTH = 20
STOCH_RSI_K = 5
STOCH_RSI_D = 5

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# =========================
# DATA FUNCTIONS
# =========================


def normalizza_dataframe_yfinance(data):
    if isinstance(data.columns, pd.MultiIndex):
        livello_0 = list(data.columns.get_level_values(0))
        livello_1 = list(data.columns.get_level_values(1))
        if "Close" in livello_0:
            data.columns = data.columns.get_level_values(0)
        elif "Close" in livello_1:
            data.columns = data.columns.get_level_values(1)
        else:
            nuove_colonne = []
            for colonna in data.columns:
                parti = [str(elemento) for elemento in colonna if str(elemento) != ""]
                nuove_colonne.append("_".join(parti))
            data.columns = nuove_colonne
    return data


@st.cache_data(ttl=900, show_spinner=False)
def scarica_dati_weekly(ticker):
    try:
        data = yf.download(
            ticker,
            period=PERIODO_DATI,
            interval=INTERVALLO_DATI,
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
    return serie.rolling(periodo).apply(lambda valori: np.dot(valori, pesi) / pesi.sum(), raw=True)


def calcola_rsi(serie, periodo):
    delta = serie.diff()
    guadagni = delta.clip(lower=0)
    perdite = -delta.clip(upper=0)
    media_guadagni = guadagni.ewm(alpha=1 / periodo, adjust=False).mean()
    media_perdite = perdite.ewm(alpha=1 / periodo, adjust=False).mean()
    rs = media_guadagni / media_perdite.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calcola_stoch_rsi(serie_close):
    rsi = calcola_rsi(serie_close, STOCH_RSI_RSI_LENGTH)
    rsi_min = rsi.rolling(STOCH_RSI_LENGTH).min()
    rsi_max = rsi.rolling(STOCH_RSI_LENGTH).max()
    stoch_rsi = ((rsi - rsi_min) / (rsi_max - rsi_min)) * 100
    stoch_rsi = stoch_rsi.replace([np.inf, -np.inf], np.nan)
    k = stoch_rsi.rolling(STOCH_RSI_K).mean()
    d = k.rolling(STOCH_RSI_D).mean()
    return k, d


def calcola_macd(serie_close):
    ema_fast = serie_close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = serie_close.ewm(span=MACD_SLOW, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=MACD_SIGNAL, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram


def prepara_indicatori_weekly(data):
    data_plot = data.copy()
    data_plot["WMA21W"] = calcola_wma(data_plot["Close"], WMA_21)
    data_plot["WMA50W"] = calcola_wma(data_plot["Close"], WMA_50)
    data_plot["WMA200W"] = calcola_wma(data_plot["Close"], WMA_200)
    data_plot["EMA200W"] = data_plot["Close"].ewm(span=EMA_200, adjust=False).mean()
    data_plot["SMA200W"] = data_plot["Close"].rolling(SMA_200).mean()
    stoch_k, stoch_d = calcola_stoch_rsi(data_plot["Close"])
    data_plot["STOCH_RSI_K"] = stoch_k
    data_plot["STOCH_RSI_D"] = stoch_d
    macd, macd_signal, macd_hist = calcola_macd(data_plot["Close"])
    data_plot["MACD"] = macd
    data_plot["MACD_SIGNAL"] = macd_signal
    data_plot["MACD_HIST"] = macd_hist
    return data_plot


def formatta_numero(valore):
    if valore is None:
        return "N/D"
    return f"{valore:.2f}"


# =========================
# CHART
# =========================


def crea_grafico_weekly(data, ticker):
    colori_macd_hist = ["#26a69a" if valore >= 0 else "#ef5350" for valore in data["MACD_HIST"].fillna(0)]
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=[0.58, 0.14, 0.14, 0.14],
        subplot_titles=(
            ticker + " - Weekly 10 anni",
            "Volume weekly",
            "Stoch RSI (20,5,5)",
            "MACD Weekly (12,26,9)"
        )
    )

    fig.add_trace(go.Candlestick(x=data.index, open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"], name=ticker, increasing_line_color="#00c087", decreasing_line_color="#ff4d4d", increasing_fillcolor="#00c087", decreasing_fillcolor="#ff4d4d"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["WMA21W"], mode="lines", name="WMA 21W", line=dict(color="#ffffff", width=1.8)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["WMA50W"], mode="lines", name="WMA 50W", line=dict(color="#26a69a", width=2.0)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["WMA200W"], mode="lines", name="WMA 200W", line=dict(color="#2962ff", width=2.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["EMA200W"], mode="lines", name="EMA 200W", line=dict(color="#ffeb3b", width=2.1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["SMA200W"], mode="lines", name="SMA 200W", line=dict(color="#ff9800", width=2.3)), row=1, col=1)

    if "Volume" in data.columns:
        fig.add_trace(go.Bar(x=data.index, y=data["Volume"], name="Volume", opacity=0.42, marker_color="#5f6b7a"), row=2, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=data["STOCH_RSI_K"], mode="lines", name="Stoch RSI K", line=dict(color="#ffffff", width=1.6)), row=3, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["STOCH_RSI_D"], mode="lines", name="Stoch RSI D", line=dict(color="#f5c542", width=1.6)), row=3, col=1)
    fig.add_hline(y=80, line_width=1, line_dash="dot", line_color="#8a99ad", row=3, col=1)
    fig.add_hline(y=20, line_width=1, line_dash="dot", line_color="#8a99ad", row=3, col=1)

    fig.add_trace(go.Bar(x=data.index, y=data["MACD_HIST"], name="MACD Histogram", marker_color=colori_macd_hist, opacity=0.55), row=4, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["MACD"], mode="lines", name="MACD", line=dict(color="#00b0ff", width=1.8)), row=4, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["MACD_SIGNAL"], mode="lines", name="Signal", line=dict(color="#ff9800", width=1.7)), row=4, col=1)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#8a99ad", row=4, col=1)

    fig.update_layout(template="plotly_dark", height=1050, margin=dict(l=10, r=55, t=70, b=10), xaxis_rangeslider_visible=False, legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1), hovermode="x unified", plot_bgcolor="#0e1117", paper_bgcolor="#0e1117")
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    fig.update_yaxes(title_text="Prezzo", row=1, col=1, side="right", showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    fig.update_yaxes(title_text="Volume", row=2, col=1, side="right", showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig.update_yaxes(title_text="Stoch RSI", row=3, col=1, side="right", range=[0, 100], showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig.update_yaxes(title_text="MACD", row=4, col=1, side="right", showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    return fig


# =========================
# PAGE
# =========================

ticker = st.session_state.get("ticker_selezionato", None)

if ticker is None:
    st.warning("Nessun ticker selezionato. Apri questa pagina dalla Watchlist usando il pulsante grafico.")
    if st.button("Torna al Cockpit"):
        st.switch_page("pages/dashboard.py")
    st.stop()

st.title("Analisi Weekly: " + ticker)
st.caption("Vista weekly a 10 anni con medie mobili, Stoch RSI (20,5,5) e MACD weekly standard (12,26,9).")

col_back, col_info = st.columns([1.2, 4.8])

with col_back:
    if st.button("Torna al Cockpit"):
        st.switch_page("pages/dashboard.py")

with col_info:
    st.info("Timeframe weekly | Periodo fisso 10 anni | Stoch RSI (20,5,5) | MACD weekly standard (12,26,9)")

with st.spinner("Caricamento dati weekly a 10 anni per " + ticker + "..."):
    data, errore_download = scarica_dati_weekly(ticker)

if errore_download:
    st.warning("Yahoo Finance/YFinance ha limitato o interrotto temporaneamente la richiesta. Riprova tra qualche minuto.")

if data.empty:
    st.error("Non sono stati trovati dati validi per il ticker " + ticker + ". Controlla il simbolo nella Watchlist.")
    if st.button("Torna al Cockpit", key="back_no_data"):
        st.switch_page("pages/dashboard.py")
    st.stop()

data = prepara_indicatori_weekly(data)

st.subheader("Metriche weekly")
metriche = {
    "prezzo": valore_float(data["Close"].iloc[-1]),
    "sma_200w": valore_float(data["SMA200W"].iloc[-1]),
    "stoch_k": valore_float(data["STOCH_RSI_K"].iloc[-1]),
    "stoch_d": valore_float(data["STOCH_RSI_D"].iloc[-1]),
    "macd": valore_float(data["MACD"].iloc[-1]),
    "macd_signal": valore_float(data["MACD_SIGNAL"].iloc[-1])
}

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
with kpi_1:
    st.metric("Prezzo attuale", formatta_numero(metriche["prezzo"]))
with kpi_2:
    st.metric("SMA 200W", formatta_numero(metriche["sma_200w"]))
with kpi_3:
    st.metric("Stoch RSI K/D", formatta_numero(metriche["stoch_k"]) + " / " + formatta_numero(metriche["stoch_d"]))
with kpi_4:
    st.metric("MACD / Signal", formatta_numero(metriche["macd"]) + " / " + formatta_numero(metriche["macd_signal"]))

st.subheader("Grafico tecnico weekly")
fig = crea_grafico_weekly(data, ticker)
st.plotly_chart(fig, use_container_width=True)

csv_data = data.to_csv(index=True).encode("utf-8")
st.download_button(label="Scarica dati weekly CSV", data=csv_data, file_name=ticker + "_weekly_10y.csv", mime="text/csv")
