import streamlit as st
import yfinance as yf
import plotly.graph_objects as stoch_rsi, k, dimport plotly.graph_objects as go


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

    rsi, stoch_rsi, stoch_k, stoch_d = calcola_stoch_rsi(data_plot["Close"])
    data_plot["RSI20W"] = rsi
    data_plot["STOCH_RSI"] = stoch_rsi
    data_plot["STOCH_RSI_K"] = stoch_k
    data_plot["STOCH_RSI_D"] = stoch_d

    macd, macd_signal, macd_hist = calcola_macd(data_plot["Close"])
    data_plot["MACD"] = macd
    data_plot["MACD_SIGNAL"] = macd_signal
    data_plot["MACD_HIST"] = macd_hist

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

    wma_21w = valore_float(data["WMA21W"].iloc[-1])
    wma_50w = valore_float(data["WMA50W"].iloc[-1])
    wma_200w = valore_float(data["WMA200W"].iloc[-1])
    ema_200w = valore_float(data["EMA200W"].iloc[-1])
    sma_200w = valore_float(data["SMA200W"].iloc[-1])

    stoch_k = valore_float(data["STOCH_RSI_K"].iloc[-1])
    stoch_d = valore_float(data["STOCH_RSI_D"].iloc[-1])
    macd = valore_float(data["MACD"].iloc[-1])
    macd_signal = valore_float(data["MACD_SIGNAL"].iloc[-1])

    distanza_sma_200w = None

    if prezzo is not None and sma_200w is not None and sma_200w != 0:
        distanza_sma_200w = ((prezzo - sma_200w) / sma_200w) * 100

    rendimento_52w = calcola_rendimento(data, 52)

    return {
        "prezzo": prezzo,
        "wma_21w": wma_21w,
        "wma_50w": wma_50w,
        "wma_200w": wma_200w,
        "ema_200w": ema_200w,
        "sma_200w": sma_200w,
        "distanza_sma_200w": distanza_sma_200w,
        "rendimento_52w": rendimento_52w,
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
        "macd": macd,
        "macd_signal": macd_signal
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
    colori_hist = [
        "#26a69a" if valore >= 0 else "#ef5350"
        for valore in data["MACD_HIST"].fillna(0)
    ]

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=[0.58, 0.14, 0.14, 0.14],
        subplot_titles=(
            f"{ticker} - Weekly 10 anni",
            "Volume weekly",
            f"Stoch RSI ({STOCH_RSI_RSI_LENGTH},{STOCH_RSI_K},{STOCH_RSI_D})",
            f"MACD Weekly ({MACD_FAST},{MACD_SLOW},{MACD_SIGNAL})"
        )
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

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["STOCH_RSI_K"],
            mode="lines",
            name=f"Stoch RSI K {STOCH_RSI_K}",
            line=dict(color="#ffffff", width=1.6)
        ),
        row=3,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["STOCH_RSI_D"],
            mode="lines",
            name=f"Stoch RSI D {STOCH_RSI_D}",
            line=dict(color="#f5c542", width=1.6)
        ),
        row=3,
        col=1
    )

    fig.add_hline(y=80, line_width=1, line_dash="dot", line_color="#8a99ad", row=3, col=1)
    fig.add_hline(y=20, line_width=1, line_dash="dot", line_color="#8a99ad", row=3, col=1)

    fig.add_trace(
        go.Bar(
            x=data.index,
            y=data["MACD_HIST"],
            name="MACD Histogram",
            marker_color=colori_hist,
            opacity=0.55
        ),
        row=4,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["MACD"],
            mode="lines",
            name=f"MACD {MACD_FAST}-{MACD_SLOW}",
            line=dict(color="#00b0ff", width=1.8)
        ),
        row=4,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["MACD_SIGNAL"],
            mode="lines",
            name=f"Signal {MACD_SIGNAL}",
            line=dict(color="#ff9800", width=1.7)
        ),
        row=4,
        col=1
    )

    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#8a99ad", row=4, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=1050,
        margin=dict(l=10, r=55, t=70, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
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

    fig.update_yaxes(
        title_text="Stoch RSI",
        row=3,
        col=1,
        side="right",
        range=[0, 100],
        showgrid=True,
        gridcolor="rgba(255,255,255,0.05)",
        zeroline=False
    )

    fig.update_yaxes(
        title_text="MACD",
        row=4,
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
            Vista a 10 anni su timeframe weekly con medie mobili, Stoch RSI (20,5,5)
            e MACD weekly standard (12,26,9).
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
    st.info(
        "Timeframe weekly · Periodo fisso 10 anni · "
        "Stoch RSI (20,5,5) · MACD weekly standard (12,26,9)"
    )


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
    st.metric("Prezzo attuale", formatta_numero(metriche["prezzo"]))

with kpi_2:
    st.metric("SMA 200W", formatta_numero(metriche["sma_200w"]))

with kpi_3:
    st.metric(
        "Stoch RSI K/D",
        f"{formatta_numero(metriche['stoch_k'])} / {formatta_numero(metriche['stoch_d'])}"
    )

with kpi_4:
    st.metric(
        "MACD / Signal",
        f"{formatta_numero(metriche['macd'])} / {formatta_numero(metriche['macd_signal'])}"
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
# PARAMETRI INDICATORI
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

    return serie.rolling(periodo).apply(
        lambda valori: np.dot(valori, pesi) / pesi.sum(),
        raw=True
    )


def calcola_rsi(serie, periodo):
    delta = serie.diff()
    guadagni = delta.clip(lower=0)
    perdite = -delta.clip(upper=0)

    media_guadagni = guadagni.ewm(alpha=1 / periodo, adjust=False).mean()
    media_perdite = perdite.ewm(alpha=1 / periodo, adjust=False).mean()

    rs = media_guadagni / media_perdite.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calcola_stoch_rsi(serie_close):
    rsi = calcola_rsi(serie_close, STOCH_RSI_RSI_LENGTH)

    rsi_min = rsi.rolling(STOCH_RSI_LENGTH).min()
    rsi_max = rsi.rolling(STOCH_RSI_LENGTH).max()

    stoch_rsi = ((rsi - rsi_min) / (rsi_max - rsi_min)) * 100
    stoch_rsi = stoch_rsi.replace([np.inf, -np.inf], np.nan)

    k = stoch_rsi.rolling(STOCH_RSI_K).mean()
    d = k.rolling(STOCH_RSI_D).mean()

