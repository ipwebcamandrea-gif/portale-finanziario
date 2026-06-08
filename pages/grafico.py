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

LINREG_LENGTH = 100
LINREG_SOURCE = "Close"
LINREG_UPPER_DEV = 2
LINREG_LOWER_DEV = 2
LINREG_FORWARD_WEEKS = 156

LABEL_OFFSET_WEEKS = 78
X_EXTRA_WEEKS = 280
MIN_LABEL_GAP_RATIO = 0.035

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


def ultimo_punto_valido(data, colonna):
    serie = data[colonna].dropna()
    if serie.empty:
        return None, None
    return serie.index[-1], float(serie.iloc[-1])


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
# LIN REG CHANNEL
# =========================


def calcola_linreg_channel(data):
    if LINREG_SOURCE not in data.columns:
        return None

    serie = data[LINREG_SOURCE].dropna()
    if len(serie) < LINREG_LENGTH:
        return None

    finestra = serie.iloc[-LINREG_LENGTH:]
    x = np.arange(LINREG_LENGTH)
    y = finestra.values.astype(float)

    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    residui = y - fitted
    deviazione = float(np.nanstd(residui))

    x_esteso = np.arange(LINREG_LENGTH + LINREG_FORWARD_WEEKS + 1)
    centro = slope * x_esteso + intercept
    upper = centro + (LINREG_UPPER_DEV * deviazione)
    lower = centro - (LINREG_LOWER_DEV * deviazione)

    date_reali = list(finestra.index)
    ultima_data = finestra.index[-1]
    date_future = [ultima_data + pd.Timedelta(weeks=i) for i in range(1, LINREG_FORWARD_WEEKS + 2)]
    date_canale = date_reali + date_future

    return pd.DataFrame(
        {
            "Upper": upper,
            "Center": centro,
            "Lower": lower
        },
        index=pd.Index(date_canale)
    )


# =========================
# LABELS
# =========================


def costruisci_label_items(data):
    items = []

    def aggiungi_media(colonna, testo, colore):
        _, valore = ultimo_punto_valido(data, colonna)
        if valore is not None:
            items.append(
                {
                    "text": ":" + testo + "  " + formatta_numero(valore),
                    "value": valore,
                    "color": colore,
                    "font_color": "#0e1117"
                }
            )

    aggiungi_media("WMA21W", "WMA 21W", "#ffffff")
    aggiungi_media("WMA50W", "WMA 50W", "#26a69a")
    aggiungi_media("WMA200W", "WMA 200W", "#2962ff")
    aggiungi_media("EMA200W", "EMA 200W", "#ffeb3b")
    aggiungi_media("SMA200W", "SMA 200W", "#ff9800")

    close_attuale = valore_float(data["Close"].iloc[-1])
    close_precedente = None
    if len(data) > 1:
        close_precedente = valore_float(data["Close"].iloc[-2])

    if close_attuale is not None:
        colore_prezzo = "#26a69a"
        if close_precedente is not None and close_attuale < close_precedente:
            colore_prezzo = "#ef5350"
        items.append(
            {
                "text": "PREZZO  " + formatta_numero(close_attuale),
                "value": close_attuale,
                "color": colore_prezzo,
                "font_color": "#ffffff"
            }
        )

    ultime_52 = data.tail(52)
    if not ultime_52.empty:
        max_52w = valore_float(ultime_52["High"].max())
        min_52w = valore_float(ultime_52["Low"].min())

        if max_52w is not None:
            items.append(
                {
                    "text": "MAX 52W  " + formatta_numero(max_52w),
                    "value": max_52w,
                    "color": "#ef5350",
                    "font_color": "#ffffff"
                }
            )

        if min_52w is not None:
            items.append(
                {
                    "text": "MIN 52W  " + formatta_numero(min_52w),
                    "value": min_52w,
                    "color": "#26a69a",
                    "font_color": "#ffffff"
                }
            )

    return items


def calcola_posizioni_label(items, data):
    if not items:
        return []

    y_min_base = valore_float(data["Low"].min())
    y_max_base = valore_float(data["High"].max())

    if y_min_base is None or y_max_base is None:
        return []

    y_range = max(y_max_base - y_min_base, 1)
    min_gap = y_range * MIN_LABEL_GAP_RATIO

    ordinati = sorted(items, key=lambda item: item["value"])
    ultimo_y = None

    for item in ordinati:
        y_originale = item["value"]
        y_label = y_originale

        if ultimo_y is not None and y_label < ultimo_y + min_gap:
            y_label = ultimo_y + min_gap

        item["label_y"] = y_label
        ultimo_y = y_label

    return ordinati


def aggiungi_label_items(fig, items, label_x):
    for item in items:
        fig.add_annotation(
            x=label_x,
            y=item["label_y"],
            xref="x",
            yref="y",
            text=item["text"],
            showarrow=False,
            font=dict(color=item["font_color"], size=11),
            align="center",
            bgcolor=item["color"],
            bordercolor=item["color"],
            borderwidth=1,
            borderpad=4,
            opacity=0.98,
            row=1,
            col=1
        )


# =========================
# CHART
# =========================


def crea_grafico_weekly(data, ticker):
    colori_macd_hist = ["#26a69a" if valore >= 0 else "#ef5350" for valore in data["MACD_HIST"].fillna(0)]
    linreg = calcola_linreg_channel(data)

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

    if linreg is not None:
        fig.add_trace(go.Scatter(x=linreg.index, y=linreg["Upper"], mode="lines", name="LinReg Upper", line=dict(color="#2962ff", width=1.4), hoverinfo="skip", opacity=0.95), row=1, col=1)
        fig.add_trace(go.Scatter(x=linreg.index, y=linreg["Center"], mode="lines", name="LinReg 100 close 2 2", line=dict(color="#ff3b3b", width=1.3), fill="tonexty", fillcolor="rgba(41, 98, 255, 0.15)", hoverinfo="skip", opacity=0.95), row=1, col=1)
        fig.add_trace(go.Scatter(x=linreg.index, y=linreg["Lower"], mode="lines", name="LinReg Lower", line=dict(color="#2962ff", width=1.4), fill="tonexty", fillcolor="rgba(255, 59, 59, 0.14)", hoverinfo="skip", opacity=0.95), row=1, col=1)

    fig.add_trace(go.Candlestick(x=data.index, open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"], name=ticker, increasing_line_color="#00c087", decreasing_line_color="#ff4d4d", increasing_fillcolor="#00c087", decreasing_fillcolor="#ff4d4d", hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["WMA21W"], mode="lines", name="WMA 21W", line=dict(color="#ffffff", width=1.8), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["WMA50W"], mode="lines", name="WMA 50W", line=dict(color="#26a69a", width=2.0), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["WMA200W"], mode="lines", name="WMA 200W", line=dict(color="#2962ff", width=2.2), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["EMA200W"], mode="lines", name="EMA 200W", line=dict(color="#ffeb3b", width=2.1), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["SMA200W"], mode="lines", name="SMA 200W", line=dict(color="#ff9800", width=2.3), hoverinfo="skip"), row=1, col=1)

    close_attuale = valore_float(data["Close"].iloc[-1])
    if close_attuale is not None:
        colore_prezzo = "#26a69a"
        if len(data) > 1:
            close_precedente = valore_float(data["Close"].iloc[-2])
            if close_precedente is not None and close_attuale < close_precedente:
                colore_prezzo = "#ef5350"
        fig.add_hline(y=close_attuale, line_width=1.2, line_dash="dash", line_color=colore_prezzo, row=1, col=1)

    ultime_52 = data.tail(52)
    max_52w = valore_float(ultime_52["High"].max()) if not ultime_52.empty else None
    min_52w = valore_float(ultime_52["Low"].min()) if not ultime_52.empty else None

    if max_52w is not None:
        fig.add_hline(y=max_52w, line_width=1.2, line_dash="dash", line_color="#ef5350", row=1, col=1)

    if min_52w is not None:
        fig.add_hline(y=min_52w, line_width=1.2, line_dash="dash", line_color="#26a69a", row=1, col=1)

    label_x = data.index.max() + pd.Timedelta(weeks=LABEL_OFFSET_WEEKS)
    label_items = costruisci_label_items(data)
    label_items = calcola_posizioni_label(label_items, data)
    aggiungi_label_items(fig, label_items, label_x)

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["Close"],
            mode="markers",
            name="Cursore",
            marker=dict(size=8, color="rgba(255,255,255,0)"),
            showlegend=False,
            hovertemplate="Data: %{x|%d/%m/%Y}<br>Prezzo: %{y:.2f}<extra></extra>"
        ),
        row=1,
        col=1
    )

    if "Volume" in data.columns:
        fig.add_trace(go.Bar(x=data.index, y=data["Volume"], name="Volume", opacity=0.42, marker_color="#5f6b7a", hoverinfo="skip"), row=2, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=data["STOCH_RSI_K"], mode="lines", name="Stoch RSI K", line=dict(color="#ffffff", width=1.6), hoverinfo="skip"), row=3, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["STOCH_RSI_D"], mode="lines", name="Stoch RSI D", line=dict(color="#f5c542", width=1.6), hoverinfo="skip"), row=3, col=1)
    fig.add_hline(y=80, line_width=1, line_dash="dot", line_color="#8a99ad", row=3, col=1)
    fig.add_hline(y=20, line_width=1, line_dash="dot", line_color="#8a99ad", row=3, col=1)

    fig.add_trace(go.Bar(x=data.index, y=data["MACD_HIST"], name="MACD Histogram", marker_color=colori_macd_hist, opacity=0.55, hoverinfo="skip"), row=4, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["MACD"], mode="lines", name="MACD", line=dict(color="#00b0ff", width=1.8), hoverinfo="skip"), row=4, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["MACD_SIGNAL"], mode="lines", name="Signal", line=dict(color="#ff9800", width=1.7), hoverinfo="skip"), row=4, col=1)
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#8a99ad", row=4, col=1)

    x_min = data.index.min()
    x_max = data.index.max() + pd.Timedelta(weeks=X_EXTRA_WEEKS)

    y_min = valore_float(data["Low"].min())
    y_max = valore_float(data["High"].max())
    if label_items:
        y_min = min(y_min, min(item["label_y"] for item in label_items))
        y_max = max(y_max, max(item["label_y"] for item in label_items))
    y_padding = max((y_max - y_min) * 0.05, 1)

    fig.update_layout(template="plotly_dark", height=1050, margin=dict(l=10, r=190, t=70, b=10), xaxis_rangeslider_visible=False, hovermode="closest", plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1))

    fig.update_xaxes(range=[x_min, x_max], showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False, showspikes=True, spikecolor="rgba(255,255,255,0.55)", spikethickness=1, spikedash="dot", spikemode="across", spikesnap="cursor")
    fig.update_yaxes(title_text="Prezzo", row=1, col=1, side="right", range=[y_min - y_padding, y_max + y_padding], showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False, showspikes=True, spikecolor="rgba(255,255,255,0.55)", spikethickness=1, spikedash="dot", spikesnap="cursor")
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
st.caption("Vista weekly a 10 anni con medie mobili, LinReg 100 close 2 2, Stoch RSI (20,5,5), MACD weekly standard (12,26,9), prezzo attuale e Max/Min 52W.")

col_back, col_info = st.columns([1.2, 4.8])

with col_back:
    if st.button("Torna al Cockpit"):
        st.switch_page("pages/dashboard.py")

with col_info:
    st.info("Label anti-sovrapposizione | Prezzo attuale tratteggiato | Crosshair tratteggiato | Max/Min 52W")

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
    "sma_200w": valore_float(data["SMA200W"].iloc[-1])
}

kpi_1, kpi_2 = st.columns(2)
with kpi_1:
    st.metric("Prezzo attuale", formatta_numero(metriche["prezzo"]))
with kpi_2:
    st.metric("SMA 200W", formatta_numero(metriche["sma_200w"]))

st.subheader("Grafico tecnico weekly")
fig = crea_grafico_weekly(data, ticker)
st.plotly_chart(fig, use_container_width=True)

csv_data = data.to_csv(index=True).encode("utf-8")
st.download_button(label="Scarica dati weekly CSV", data=csv_data, file_name=ticker + "_weekly_10y.csv", mime="text/csv")
