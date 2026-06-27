import pandas as pd
import streamlit as st
import yfinance as yf

from utils.symbols import normalize_yfinance_symbol


# =========================
# HELPERS DATI YFINANCE
# =========================

def normalizza_dataframe_yfinance(data):
    if isinstance(data.columns, pd.MultiIndex):
        livello_0 = list(data.columns.get_level_values(0))
        livello_1 = list(data.columns.get_level_values(1))

        if "Close" in livello_0:
            data.columns = data.columns.get_level_values(0)
        elif "Close" in livello_1:
            data.columns = data.columns.get_level_values(1)

    return data


def valore_float_sicuro(value):
    if isinstance(value, pd.Series):
        value = value.dropna()
        if value.empty:
            return None
        value = value.iloc[0]

    if value is None or pd.isna(value):
        return None

    return float(value)


# =========================
# METRICHE FINANZIARIE
# =========================

@st.cache_data(ttl=120, show_spinner=False)
def get_stock_metrics(symbol):
    yf_symbol = normalize_yfinance_symbol(symbol)

    try:
        last_price = None
        previous_close = None
        currency = ""
        short_name = ""
        long_name = ""

        try:
            intraday = yf.download(yf_symbol, period="5d", interval="15m", auto_adjust=False, progress=False, threads=False)

            if intraday is not None and not intraday.empty:
                intraday = normalizza_dataframe_yfinance(intraday)

                if "Close" in intraday.columns:
                    intraday = intraday.dropna(subset=["Close"])

                    if not intraday.empty:
                        last_price = valore_float_sicuro(intraday["Close"].iloc[-1])
        except Exception:
            pass

        try:
            daily = yf.download(yf_symbol, period="10d", interval="1d", auto_adjust=False, progress=False, threads=False)

            if daily is not None and not daily.empty:
                daily = normalizza_dataframe_yfinance(daily)

                if "Close" in daily.columns:
                    daily = daily.dropna(subset=["Close"])

                    if len(daily) >= 2:
                        previous_close = valore_float_sicuro(daily["Close"].iloc[-2])
                    elif len(daily) == 1:
                        previous_close = valore_float_sicuro(daily["Close"].iloc[-1])
        except Exception:
            pass

        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.fast_info

            def fast_value(*keys):
                for key in keys:
                    try:
                        value = info.get(key, None)
                    except Exception:
                        try:
                            value = info[key]
                        except Exception:
                            value = None

                    if value is not None:
                        return value

                return None

            if last_price is None:
                last_price = valore_float_sicuro(fast_value("last_price", "lastPrice", "regularMarketPrice"))

            if previous_close is None:
                previous_close = valore_float_sicuro(fast_value("previous_close", "previousClose", "regularMarketPreviousClose"))

            currency = fast_value("currency") or ""

            try:
                full_info = ticker.get_info()
                short_name = full_info.get("shortName") or full_info.get("displayName") or ""
                long_name = full_info.get("longName") or ""
            except Exception:
                pass
        except Exception:
            pass

        sma200 = None
        dist_pct = None
        hist_min_w_pct = None
        hist_max_w_pct = None

        try:
            weekly = yf.download(yf_symbol, period="10y", interval="1wk", auto_adjust=False, progress=False, threads=False)

            if weekly is not None and not weekly.empty:
                weekly = normalizza_dataframe_yfinance(weekly)

                if "Close" in weekly.columns:
                    weekly = weekly.dropna(subset=["Close"])

                    if last_price is None and not weekly.empty:
                        last_price = valore_float_sicuro(weekly["Close"].iloc[-1])

                    if len(weekly) >= 200:
                        sma200_series = weekly["Close"].rolling(200).mean()
                        sma200 = valore_float_sicuro(sma200_series.iloc[-1])

                        if sma200 is not None and sma200 != 0 and last_price is not None:
                            dist_pct = ((last_price - sma200) / sma200) * 100

                        # Estremi storici weekly rispetto alla SMA200W.
                        # Hist Min W replica la logica TradingView: movimento da SMA200W a Low weekly,
                        # usando la SMA200W come base percentuale e mostrando il risultato negativo.
                        # Hist Max W misura l'estensione da SMA200W a High weekly, usando la SMA200W come base.
                        if "Low" in weekly.columns and "High" in weekly.columns:
                            hist_source = weekly.copy()
                            hist_source["SMA200W"] = sma200_series
                            hist_source = hist_source.dropna(subset=["Low", "High", "SMA200W"])
                            hist_source = hist_source[
                                (hist_source["Low"] > 0) &
                                (hist_source["High"] > 0) &
                                (hist_source["SMA200W"] > 0)
                            ]

                            below_sma = hist_source[hist_source["Low"] < hist_source["SMA200W"]]
                            if not below_sma.empty:
                                sma_to_min = ((below_sma["SMA200W"] - below_sma["Low"]) / below_sma["SMA200W"]) * 100
                                max_drawdown_to_low = valore_float_sicuro(sma_to_min.max())
                                if max_drawdown_to_low is not None:
                                    hist_min_w_pct = -max_drawdown_to_low

                            above_sma = hist_source[hist_source["High"] > hist_source["SMA200W"]]
                            if not above_sma.empty:
                                sma_to_max = ((above_sma["High"] - above_sma["SMA200W"]) / above_sma["SMA200W"]) * 100
                                hist_max_w_pct = valore_float_sicuro(sma_to_max.max())
        except Exception:
            pass

        daily_change_pct = None

        if last_price is not None and previous_close is not None and previous_close != 0:
            daily_change_pct = ((last_price - previous_close) / previous_close) * 100

        return {
            "symbol": symbol,
            "yf_symbol": yf_symbol,
            "last_price": last_price,
            "daily_change_pct": daily_change_pct,
            "sma200w": sma200,
            "dist_pct": dist_pct,
            "hist_min_w_pct": hist_min_w_pct,
            "hist_max_w_pct": hist_max_w_pct,
            "currency": currency or "",
            "name": short_name or long_name or "",
            "short_name": short_name or "",
            "long_name": long_name or "",
        }
    except Exception:
        return {
            "symbol": symbol,
            "yf_symbol": yf_symbol,
            "last_price": None,
            "daily_change_pct": None,
            "sma200w": None,
            "dist_pct": None,
            "hist_min_w_pct": None,
            "hist_max_w_pct": None,
            "currency": "",
            "name": "",
            "short_name": "",
            "long_name": "",
        }


def is_in_sma200_zone(dist_pct):
    # Attenzione SMA200W: in zona ±10% oppure sotto la SMA200W oltre la zona.
    # In pratica: tutte le distanze <= +10% sono evidenziate.
    return dist_pct is not None and dist_pct <= 10


def watchlist_has_sma200_zone(name):
    symbols = st.session_state["tv_watchlists_data"]["watchlists"].get(name, [])

    for symbol in symbols:
        metrics = get_stock_metrics(symbol)

        if is_in_sma200_zone(metrics["dist_pct"]):
            return True

    return False
