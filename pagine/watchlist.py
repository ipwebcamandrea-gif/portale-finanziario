import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide")
st.title("Portale SMA 200W & Analisi Grafica Professionale")

# 1. Configurazione Input nella Sidebar
st.sidebar.header("Impostazioni Watchlist")
tickers_input = st.sidebar.text_input(
    "Modifica i Ticker (separati da virgola):", 
    "AAPL, MSFT, AMZN, GOOGL, BRK-B, NVDA, META"
)

soglia_percentuale = st.sidebar.slider(
    "Soglia di vicinanza alla SMA 200 (%)", 
    min_value=1.0, max_value=10.0, value=10.0, step=0.5
)
soglia_decimal = soglia_percentuale / 100

tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

def calcola_wma(serie, window):
    pesi = np.arange(1, window + 1)
    return serie.rolling(window).apply(lambda x: np.dot(x, pesi) / pesi.sum(), raw=True)

# 2. Funzione per la tabella (Cache 60s) con storico completo
@st.cache_data(ttl=60)
def elabora_watchlist(lista_ticker, soglia):
    tabella_dati = []
    for ticker in lista_ticker:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="max", interval="1wk")
            
            if hist.empty or len(hist) < 200:
                tabella_dati.append({
                    "Ticker": ticker, "Prezzo Attuale": np.nan, "SMA 200 W": np.nan, 
                    "Distanza %": np.nan, "Trigger": False, "Nota": "Storico insufficiente"
                })
                continue
                
            hist.index = hist.index.tz_localize(None)
            hist['SMA_200_W'] = hist['Close'].rolling(window=200).mean()
            
            prezzo_attuale = hist['Close'].iloc[-1]
            sma_200_w = hist['SMA_200_W'].iloc[-1]
            distanza = (prezzo_attuale - sma_200_w) / sma_200_w
            vicino_alla_media = abs(distanza) <= soglia
            
            tabella_dati.append({
                "Ticker": ticker, "Prezzo Attuale": prezzo_attuale, "SMA 200 W": sma_200_w,
                "Distanza %": distanza * 100, "Trigger": vicino_alla_media, "Nota": "OK"
            })
        except Exception:
            tabella_dati.append({
                "Ticker": ticker, "Prezzo Attuale": np.nan, "SMA 200 W": np.nan, 
                "Distanza %": np.nan, "Trigger": False, "Nota": "Errore caricamento"
            })
    return pd.DataFrame(tabella_dati)

# 3. Visualizzazione Tabella Realtime
@st.fragment(run_every="2m")
def mostra_tabella_realtime():
    df_watchlist = elabora_watchlist(tickers, soglia_decimal)
    def colora_righe(row):
        if row['Trigger'] == True:
            return ['background-color: #fff3cd; color: #856404; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    st.subheader("Titoli monitorati (Refresh automatico ogni 2m)")
    st.dataframe(
        df_watchlist.style.apply(colora_righe, axis=1), 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Prezzo Attuale": st.column_config.NumberColumn(format="$ %.2f"),
            "SMA 200 W": st.column_config.NumberColumn(format="$ %.2f"),
            "Distanza %": st.column_config.NumberColumn(format="%.2f %%"),
            "Trigger": None
        }
    )

# 4. Logica Grafica Avanzata (Plotly stile TradingView)
if tickers:
    mostra_tabella_realtime()
    st.markdown("---")
    
    ticker_selezionato = st.selectbox("Seleziona un titolo per l'analisi grafica:", tickers)
    
    if ticker_selezionato:
        stock = yf.Ticker(ticker_selezionato)
        df_chart = stock.history(period="max", interval="1wk")
        
        if len(df_chart) >= 200:
            df_chart.index = df_chart.index.tz_localize(None)
            
            # Parametri Configurazione Indicatori (Modificabili centralmente)
            param_macd = {"fast": 12, "slow": 26, "signal": 9}
            param_stochrsi = {"rsi_len": 20, "stoch_len": 20, "k": 5, "d": 5}
            
            # Calcolo Medie Mobili
            df_chart['WMA21'] = calcola_wma(df_chart['Close'], 21)
            df_chart['WMA50'] = calcola_wma(df_chart['Close'], 50)
            df_chart['WMA200'] = calcola_wma(df_chart['Close'], 200)
            df_chart['EMA200'] = df_chart['Close'].ewm(span=200, adjust=False).mean()
            df_chart['SMA200'] = df_chart['Close'].rolling(window=200).mean()
            
            # MACD con parametri dinamici
            df_chart['EMA_Fast'] = df_chart['Close'].ewm(span=param_macd["fast"], adjust=False).mean()
            df_chart['EMA_Slow'] = df_chart['Close'].ewm(span=param_macd["slow"], adjust=False).mean()
            df_chart['MACD'] = df_chart['EMA_Fast'] - df_chart['EMA_Slow']
            df_chart['MACD_Signal'] = df_chart['MACD'].ewm(span=param_macd["signal"], adjust=False).mean()
            df_chart['MACD_Hist'] = df_chart['MACD'] - df_chart['MACD_Signal']
            
            # Stoch RSI con parametri dinamici
            delta = df_chart['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=param_stochrsi["rsi_len"]).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=param_stochrsi["rsi_len"]).mean()
            rs = gain / loss.replace(0, np.inf)
            df_chart['RSI'] = 100 - (100 / (1 + rs))
            rsi_min = df_chart['RSI'].rolling(window=param_stochrsi["stoch_len"]).min()
            rsi_max = df_chart['RSI'].rolling(window=param_stochrsi["stoch_len"]).max()
            df_chart['StochRSI'] = (df_chart['RSI'] - rsi_min) / (rsi_max - rsi_min) * 100
            df_chart['StochRSI_K'] = df_chart['StochRSI'].rolling(window=param_stochrsi["k"]).mean()
            df_chart['StochRSI_D'] = df_chart['StochRSI_K'].rolling(window=param_stochrsi["d"]).mean()
            
            # Filtro temporale dal 2019 ad oggi
            df_plot = df_chart.loc["2019-01-01":].copy()
            
            # Estrazione valori correnti (ultimo punto utile) per Legende e Label
            prezzo_ult = df_plot['Close'].iloc[-1]
            wma21_ult = df_plot['WMA21'].iloc[-1]
            wma50_ult = df_plot['WMA50'].iloc[-1]
            wma200_ult = df_plot['WMA200'].iloc[-1]
            ema200_ult = df_plot['EMA200'].iloc[-1]
            sma200_ult = df_plot['SMA200'].iloc[-1]
            
            # Calcolo Massimi e Minimi delle ultime 52 settimane (52 candele settimanali)
            df_52w = df_plot.tail(52)
            max_52w = float(df_52w['High'].max())
            min_52w = float(df_52w['Low'].min())
            
            dist_sma200 = ((prezzo_ult - sma200_ult) / sma200_ult) * 100
            dist_max52w = ((prezzo_ult - max_52w) / max_52w) * 100
            dist_min52w = ((prezzo_ult - min_52w) / min_52w) * 100
            
            # RISOLUZIONE DEL PROBLEMA DELLE SCRITTE COPERTE:
            # Mostriamo il titolo del timeframe fuori da Plotly tramite Streamlit
            st.subheader(f"Grafico Avanzato {ticker_selezionato} • Timeframe: 1 Settimana (Weekly)")
            
            # Creazione Layout del grafico
            fig = make_subplots(
                rows=3, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.04, 
                row_heights=[0.60, 0.20, 0.20],
                specs=[[{"secondary_y": True}], [{}], [{}]]
            )
            
            # Candlestick Principale
            fig.add_trace(go.Candlestick(
                x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                low=df_plot['Low'], close=df_plot['Close'], name="Prezzo",
                increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
                decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
            ), row=1, col=1, secondary_y=False)
            
            # Tracciamento Medie Mobili con valori correnti inseriti nella legenda (Etichette)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['WMA21'], line=dict(color='white', width=1.2), name=f'WMA 21 ({wma21_ult:.2f})'), row=1, col=1, secondary_y=False)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['WMA50'], line=dict(color='green', width=1.2), name=f'WMA 50 ({wma50_ult:.2f})'), row=1, col=1, secondary_y=False)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['WMA200'], line=dict(color='#00bcff', width=1.2), name=f'WMA 200 ({wma200_ult:.2f})'), row=1, col=1, secondary_y=False)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA200'], line=dict(color='yellow', width=1.2), name=f'EMA 200 ({ema200_ult:.2f})'), row=1, col=1, secondary_y=False)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], line=dict(color='orange', width=2), name=f'SMA 200 W ({sma200_ult:.2f})'), row=1, col=1, secondary_y=False)
            
            # Tracciamento Linee Orizzontali Max/Min 52 Settimane
            fig.add_trace(go.Scatter(
                x=[df_plot.index[0], df_plot.index[-1]], y=[max_52w, max_52w],
                line=dict(color='#ff3399', width=1.5, dash='dash'), name=f'Max 52W ({max_52w:.2f})'
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=[df_plot.index[0], df_plot.index[-1]], y=[min_52w, min_52w],
                line=dict(color='#33ccff', width=1.5, dash='dash'), name=f'Min 52W ({min_52w:.2f})'
            ), row=1, col=1)
            
            # NUOVO REQUISITO: Linea Orizzontale tratteggiata della quotazione attuale del prezzo
            fig.add_trace(go.Scatter(
                x=[df_plot.index[0], df_plot.index[-1]], y=[prezzo_ult, prezzo_ult],
                line=dict(color='#e0e0e0', width=1.2, dash='dot'), name=f'Quota Corrente ({prezzo_ult:.2f})'
            ), row=1, col=1)
            
            # Label dinamiche sul lato destro (prezzo e distanza % dal valore attuale)
            # Label Quota Corrente
            fig.add_annotation(
                x=df_plot.index[-1], y=prezzo_ult, text=f"Quota Corrente: {prezzo_ult:.2f}",
                align="left", showarrow=False, xanchor="left", xshift=8,
                font=dict(size=11, color="black"), bgcolor="#e0e0e0", bordercolor="#e0e0e0", borderwidth=1, row=1, col=1
            )
            # Label SMA 200
            fig.add_annotation(
                x=df_plot.index[-1], y=sma200_ult, text=f"SMA200: {sma200_ult:.2f} ({dist_sma200:+.2f}%)",
                align="left", showarrow=False, xanchor="left", xshift=8,
                font=dict(size=11, color="black"), bgcolor="orange", bordercolor="orange", borderwidth=1, row=1, col=1
            )
            # Label Max 52W
            fig.add_annotation(
                x=df_plot.index[-1], y=max_52w, text=f"Max 52W: {max_52w:.2f} ({dist_max52w:+.2f}%)",
                align="left", showarrow=False, xanchor="left", xshift=8,
                font=dict(size=11, color="white"), bgcolor="#ff3399", bordercolor="#ff3399", borderwidth=1, row=1, col=1
            )
            # Label Min 52W
            fig.add_annotation(
                x=df_plot.index[-1], y=min_52w, text=f"Min 52W: {min_52w:.2f} ({dist_min52w:+.2f}%)",
                align="left", showarrow=False, xanchor="left", xshift=8,
                font=dict(size=11, color="black"), bgcolor="#33ccff", bordercolor="#33ccff", borderwidth=1, row=1, col=1
            )
            
            # Volumi in secondo piano overlay
            colori_volumi = ['rgba(38, 166, 154, 0.12)' if c >= o else 'rgba(239, 83, 80, 0.12)' 
                             for c, o in zip(df_plot['Close'], df_plot['Open'])]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], marker_color=colori_volumi, name="Volume", showlegend=False), row=1, col=1, secondary_y=True)
            
            # Pannello 2: Stochastic RSI con indicazione parametri in Legenda
            label_stochrsi = f"Stoch RSI ({param_stochrsi['rsi_len']},{param_stochrsi['stoch_len']},{param_stochrsi['k']},{param_stochrsi['d']})"
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['StochRSI_K'], line=dict(color='#17a2b8', width=1.5), name=f"{label_stochrsi} - %K"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['StochRSI_D'], line=dict(color='#ffc107', width=1.2), name=f"{label_stochrsi} - %D"), row=2, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="rgba(255,255,255,0.1)", row=2, col=1)
            fig.add_hline(y=80, line_dash="dash", line_color="rgba(255,255,255,0.1)", row=2, col=1)
            
            # Pannello 3: MACD con indicazione parametri in Legenda
            label_macd = f"MACD ({param_macd['fast']},{param_macd['slow']},{param_macd['signal']})"
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MACD'], line=dict(color='#007bff', width=1.5), name=label_macd), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MACD_Signal'], line=dict(color='#dc3545', width=1.5), name="Signal"), row=3, col=1)
            colori_macd_hist = ['#26a69a' if val >= 0 else '#ef5350' for val in df_plot['MACD_Hist']]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['MACD_Hist'], marker_color=colori_macd_hist, name='Hist'), row=3, col=1)
            
            # Layout Stile TradingView Dark Ottimizzato (Senza sovrapposizioni)
            fig.update_layout(
                template="plotly_dark",
                height=950,
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=150, t=30, b=10), # Margine superiore abbassato e destro allargato a 150 per le scritte lunghe
                paper_bgcolor='#131722',
                plot_bgcolor='#131722',
                showlegend=True,
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="left", 
                    x=0, 
                    font=dict(size=11),
                    bgcolor="rgba(19, 23, 34, 0.8)" # Sfondo scuro semitrasparente protettivo per i testi
                ),
                hovermode="x unified",
                hoverlabel=dict(bgcolor="#1c212e", font_size=12, font_family="Consolas")
            )
            
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.02)')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.02)', row=1, col=1, secondary_y=False)
            
            max_vol = df_plot['Volume'].max() if not df_plot['Volume'].empty else 1
            fig.update_yaxes(range=[0, max_vol * 4], showgrid=False, showticklabels=False, row=1, col=1, secondary_y=True)
            fig.update_yaxes(range=[-5, 105], row=2, col=1)
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.02)', row=3, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Storico insufficiente su questo titolo per effettuare l'analisi.")
else:
    st.info("Configura la lista dei ticker nella barra laterale.")