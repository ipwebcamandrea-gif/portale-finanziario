import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
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
        data.columns = data.columns.get_level_values(0)

    return data


@st.cache_data(ttl=900, show_spinner=False)
def scarica_dati(ticker, periodo):
    data = yf.download(
        ticker,
        period=periodo,
        interval="1d",
        progress=False,
        auto_adjust=False
    )

    if data is None or data.empty:
        return pd.DataFrame()

    data = normalizza_dataframe_yfinance(data)

    colonne_richieste = ["Open", "High", "Low", "Close"]

    for colonna in colonne_richieste:
        if colonna not in data.columns:
            return pd.DataFrame()

    data = data.dropna(subset=colonne_richieste)

    return data


def valore_float(valore):
    if isinstance(valore, pd.Series):
        valore = valore.dropna()

        if valore.empty:
            return None

        valore = valore.iloc[0]

    if pd.isna(valore):
        return None

    return float(valore)


def calcola_rendimento(data, giorni):
    if data is None or data.empty:
        return None

    if len(data) <= giorni:
        return None

    prezzo_attuale = valore_float(data["Close"].iloc[-1])
    prezzo_passato = valore_float(data["Close"].iloc[-giorni])

    if prezzo_attuale is None or prezzo_passato is None:
        return None

    if prezzo_passato == 0:
        return None

    return ((prezzo_attuale - prezzo_passato) / prezzo_passato) * 100


def calcola_metriche(data):
    prezzo = valore_float(data["Close"].iloc[-1])
    max_periodo = valore_float(data["High"].max())
    min_periodo = valore_float(data["Low"].min())

    sma_50 = valore_float(data["Close"].rolling(50).mean().iloc[-1])
    sma_200 = valore_float(data["Close"].rolling(200).mean().iloc[-1])

    rendimento_1m = calcola_rendimento(data, 21)
    rendimento_6m = calcola_rendimento(data, 126)
    rendimento_1y = calcola_rendimento(data, 252)

    distanza_sma_200 = None

    if prezzo is not None and sma_200 is not None and sma_200 != 0:
        distanza_sma_200 = ((prezzo - sma_200) / sma_200) * 100

    return {
        "prezzo": prezzo,
        "max_periodo": max_periodo,
        "min_periodo": min_periodo,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "rendimento_1m": rendimento_1m,
        "rendimento_6m": rendimento_6m,
        "rendimento_1y": rendimento_1y,
        "distanza_sma_200": distanza_sma_200
    }


# =========================
# FUNZIONI FORMATTAZIONE
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


def render_kpi_card(label, value, note=None, css_class=None):
    classe_extra = css_class if css_class else ""

    if note is None:
        note = ""

    st.markdown(
        f"""
        <div class="grafico-kpi-card">
            <div class="grafico-kpi-label">{label}</div>
            <div class="grafico-kpi-value {classe_extra}">{value}</div>
            <div class="grafico-kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# FUNZIONE GRAFICO
# =========================

def crea_grafico(data, ticker, tipo_grafico):
    data_plot = data.copy()

    data_plot["SMA50"] = data_plot["Close"].rolling(50).mean()
    data_plot["SMA200"] = data_plot["Close"].rolling(200).mean()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75, 0.25],
        subplot_titles=(f"Andamento {ticker}", "Volume")
    )

    if tipo_grafico == "Candlestick":
        fig.add_trace(
            go.Candlestick(
                x=data_plot.index,
                open=data_plot["Open"],
                high=data_plot["High"],
                low=data_plot["Low"],
                close=data_plot["Close"],
                name=ticker
            ),
            row=1,
            col=1
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=data_plot.index,
                y=data_plot["Close"],
                mode="lines",
                name="Close",
                line=dict(width=2)
            ),
            row=1,
            col=1
        )

    fig.add_trace(
        go.Scatter(
            x=data_plot.index,
            y=data_plot["SMA50"],
            mode="lines",
            name="SMA 50",
            line=dict(width=1.4)
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data_plot.index,
            y=data_plot["SMA200"],
            mode="lines",
            name="SMA 200",
            line=dict(width=1.4)
        ),
        row=1,
        col=1
    )

    if "Volume" in data_plot.columns:
        fig.add_trace(
            go.Bar(
                x=data_plot.index,
                y=data_plot["Volume"],
                name="Volume",
                opacity=0.45
            ),
            row=2,
            col=1
        )

    fig.update_layout(
        template="plotly_dark",
        height=720,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
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


st.markdown(
    f"""
    <div class="grafico-header">
        <div class="grafico-title">Analisi Quantitativa: {ticker}</div>
        <div class="grafico-subtitle">
            Dettaglio tecnico aperto dalla Watchlist. Include SMA 50, SMA 200,
            volume, rendimento e download dati.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# CONTROLLI
# =========================

st.markdown(
    """
    <div class="grafico-control-panel">
        <div class="grafico-control-title">Impostazioni grafico</div>
        <div class="grafico-control-subtitle">
            Seleziona periodo e tipo di visualizzazione.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

col_periodo, col_tipo, col_back = st.columns([1.2, 1.2, 2])

with col_periodo:
    periodo_label = st.selectbox(
        "Periodo",
        ["6 mesi", "1 anno", "2 anni", "5 anni"],
        index=2
    )

with col_tipo:
    tipo_grafico = st.selectbox(
        "Tipo grafico",
        ["Candlestick", "Linea"],
        index=0
    )

with col_back:
    st.write("")
    st.write("")
    if st.button("⬅️ Torna al Cockpit"):
        st.switch_page("pages/dashboard.py")


mappa_periodi = {
    "6 mesi": "6mo",
    "1 anno": "1y",
    "2 anni": "2y",
    "5 anni": "5y"
}

periodo_yfinance = mappa_periodi[periodo_label]


# =========================
# DOWNLOAD DATI
# =========================

with st.spinner(f"Caricamento dati per {ticker}..."):
    data = scarica_dati(ticker, periodo_yfinance)

if data.empty:
    st.markdown(
        f"""
        <div class="grafico-status-card">
            <div class="grafico-status-title">Dati non disponibili</div>
            <div class="grafico-status-text">
                Non sono stati trovati dati validi per il ticker {ticker}.
                Controlla il simbolo nella Watchlist.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("⬅️ Torna al Cockpit", key="back_no_data"):
        st.switch_page("pages/dashboard.py")

    st.stop()


# =========================
# METRICHE
# =========================

metriche = calcola_metriche(data)

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

with kpi_1:
    render_kpi_card(
        "Prezzo attuale",
        formatta_numero(metriche["prezzo"]),
        f"Periodo: {periodo_label}"
    )

with kpi_2:
    render_kpi_card(
        "SMA 200",
        formatta_numero(metriche["sma_200"]),
        "Media mobile 200 giorni"
    )

with kpi_3:
    distanza = metriche["distanza_sma_200"]
    render_kpi_card(
        "Distanza SMA 200",
        formatta_percentuale(distanza),
        "Sopra/sotto media",
        classe_valore(distanza)
    )

with kpi_4:
    rendimento_1y = metriche["rendimento_1y"]
    render_kpi_card(
        "Rendimento 1Y",
        formatta_percentuale(rendimento_1y),
        "Ultimi 252 giorni",
        classe_valore(rendimento_1y)
    )


kpi_5, kpi_6, kpi_7, kpi_8 = st.columns(4)

with kpi_5:
    render_kpi_card(
        "Max periodo",
        formatta_numero(metriche["max_periodo"]),
        "Massimo nel periodo"
    )

with kpi_6:
    render_kpi_card(
        "Min periodo",
        formatta_numero(metriche["min_periodo"]),
        "Minimo nel periodo"
    )

with kpi_7:
    rendimento_1m = metriche["rendimento_1m"]
    render_kpi_card(
        "Rendimento 1M",
        formatta_percentuale(rendimento_1m),
        "Ultimi 21 giorni",
        classe_valore(rendimento_1m)
    )

with kpi_8:
    rendimento_6m = metriche["rendimento_6m"]
    render_kpi_card(
        "Rendimento 6M",
        formatta_percentuale(rendimento_6m),
        "Ultimi 126 giorni",
        classe_valore(rendimento_6m)
    )


# =========================
# GRAFICO
# =========================

st.markdown(
    """
    <div class="grafico-chart-card">
        <div class="grafico-section-title">Grafico tecnico</div>
        <div class="grafico-section-subtitle">
            Prezzo, medie mobili e volumi.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

fig = crea_grafico(data, ticker, tipo_grafico)
st.plotly_chart(fig, use_container_width=True)


# =========================
# EXPORT DATI
# =========================

csv_data = data.to_csv(index=True).encode("utf-8")

st.download_button(
    label="⬇️ Scarica dati CSV",
    data=csv_data,
    file_name=f"{ticker}_storico.csv",
    mime="text/csv"
)
