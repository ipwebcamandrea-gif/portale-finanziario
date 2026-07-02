from __future__ import annotations

import math
import os
import time
import urllib.parse
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

TIMEZONE = ZoneInfo("Europe/Rome")
SMA_WEEKS = 200
BUY_ZONE_THRESHOLD = 65.0
STRONG_BUY_ZONE_THRESHOLD = 80.0
SMA200_HIST_MIN_PROXIMITY_POINTS = 10.0
SMA200_HIST_MIN_DIST_LIMIT = 0.0
MAX_SIMULATED_DISCOUNT_PCT = 60.0
SIMULATION_STEP_PCT = 0.5
SLEEP_BETWEEN_TICKERS_SECONDS = float(os.getenv("INSTITUTIONAL_SCANNER_SLEEP", "0.35"))
YF_REPAIR = os.getenv("YF_REPAIR", "false").strip().lower() in {"1", "true", "yes", "y"}

SYMBOLS = [
    {"ticker": "TSLA", "yahoo": "TSLA", "tv": "NASDAQ:TSLA", "name": "Tesla"},
    {"ticker": "COST", "yahoo": "COST", "tv": "NASDAQ:COST", "name": "Costco"},
    {"ticker": "MSFT", "yahoo": "MSFT", "tv": "NASDAQ:MSFT", "name": "Microsoft"},
    {"ticker": "V", "yahoo": "V", "tv": "NYSE:V", "name": "Visa"},
    {"ticker": "MA", "yahoo": "MA", "tv": "NYSE:MA", "name": "Mastercard"},
    {"ticker": "ORCL", "yahoo": "ORCL", "tv": "NYSE:ORCL", "name": "Oracle"},
    {"ticker": "PG", "yahoo": "PG", "tv": "NYSE:PG", "name": "Procter & Gamble"},
    {"ticker": "JNJ", "yahoo": "JNJ", "tv": "NYSE:JNJ", "name": "Johnson & Johnson"},
    {"ticker": "KO", "yahoo": "KO", "tv": "NYSE:KO", "name": "Coca-Cola"},
    {"ticker": "PEP", "yahoo": "PEP", "tv": "NASDAQ:PEP", "name": "PepsiCo"},
    {"ticker": "MCD", "yahoo": "MCD", "tv": "NYSE:MCD", "name": "McDonald's"},
    {"ticker": "ABT", "yahoo": "ABT", "tv": "NYSE:ABT", "name": "Abbott Laboratories"},
    {"ticker": "WMT", "yahoo": "WMT", "tv": "NYSE:WMT", "name": "Walmart"},
    {"ticker": "AAPL", "yahoo": "AAPL", "tv": "NASDAQ:AAPL", "name": "Apple"},
    {"ticker": "GOOG", "yahoo": "GOOG", "tv": "NASDAQ:GOOG", "name": "Alphabet Class C"},
    {"ticker": "BRK.B", "yahoo": "BRK-B", "tv": "NYSE:BRK.B", "name": "Berkshire Hathaway"},
    {"ticker": "NVDA", "yahoo": "NVDA", "tv": "NASDAQ:NVDA", "name": "NVIDIA"},
    {"ticker": "ASML", "yahoo": "ASML", "tv": "NASDAQ:ASML", "name": "ASML Holding"},
    {"ticker": "META", "yahoo": "META", "tv": "NASDAQ:META", "name": "Meta Platforms"},
    {"ticker": "IBM", "yahoo": "IBM", "tv": "NYSE:IBM", "name": "IBM"},
    {"ticker": "AVGO", "yahoo": "AVGO", "tv": "NASDAQ:AVGO", "name": "Broadcom"},
    {"ticker": "AXP", "yahoo": "AXP", "tv": "NYSE:AXP", "name": "American Express"},
    {"ticker": "AMZN", "yahoo": "AMZN", "tv": "NASDAQ:AMZN", "name": "Amazon"},
    {"ticker": "CRM", "yahoo": "CRM", "tv": "NYSE:CRM", "name": "Salesforce"},
]

FUNDAMENTAL_FIELDS = {
    "valuation": ["forward_pe", "peg_ratio", "fcf_yield_pct", "price_to_sales", "target_upside_pct"],
    "quality": ["return_on_equity_pct", "operating_margin_pct", "profit_margin_pct", "gross_margin_pct", "free_cashflow"],
    "growth": ["revenue_growth_pct", "earnings_growth_pct", "recommendation_mean"],
    "risk": ["beta"],
}


def now_rome() -> datetime:
    return datetime.now(TIMEZONE)


def safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        out = float(value)
        if pd.isna(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def fmt_num(value: Any, digits: int = 1) -> str:
    v = safe_float(value)
    return "N/D" if v is None else f"{v:.{digits}f}".replace(".", ",")


def fmt_price(value: Any, currency: str = "") -> str:
    v = safe_float(value)
    if v is None:
        return "N/D"
    txt = f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    cur = str(currency or "").strip().upper()
    return txt + (f" {cur}" if cur else "")


def fmt_pct(value: Any, digits: int = 1) -> str:
    v = safe_float(value)
    return "N/D" if v is None else f"{v:+.{digits}f}%".replace(".", ",")


def fmt_gap_points(value: Any) -> str:
    v = safe_float(value)
    return "N/D" if v is None else f"{abs(v):.1f}".replace(".", ",") + " pt"


def normalize_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        if "Close" in out.columns.get_level_values(0):
            out.columns = out.columns.get_level_values(0)
        elif "Close" in out.columns.get_level_values(-1):
            out.columns = out.columns.get_level_values(-1)
    return out


def yf_download(symbol: str, **kwargs) -> pd.DataFrame:
    if YF_REPAIR:
        return yf.download(symbol, repair=True, progress=False, threads=False, **kwargs)
    return yf.download(symbol, progress=False, threads=False, **kwargs)


FUNDAMENTAL_INFO_KEYS = (
    "marketCap",
    "forwardPE",
    "trailingPE",
    "pegRatio",
    "trailingPegRatio",
    "priceToSalesTrailing12Months",
    "freeCashflow",
    "returnOnEquity",
    "grossMargins",
    "operatingMargins",
    "profitMargins",
    "debtToEquity",
    "revenueGrowth",
    "earningsGrowth",
    "beta",
    "targetMeanPrice",
    "recommendationMean",
)

GET_INFO_RETRY_COUNT = int(os.getenv("INSTITUTIONAL_GET_INFO_RETRY_COUNT", "3"))
GET_INFO_RETRY_SLEEP_SECONDS = float(os.getenv("INSTITUTIONAL_GET_INFO_RETRY_SLEEP", "0.85"))


def info_has_useful_fundamentals(info: dict[str, Any] | None) -> bool:
    """Return True only when yfinance info contains at least some useful fundamentals.

    Yahoo/yfinance can occasionally return an empty or almost-empty dict inside
    Streamlit/cloud while historical price downloads still work. Treat those
    responses as failed attempts and retry before accepting missing fundamentals.
    """
    if not isinstance(info, dict) or not info:
        return False
    useful_count = 0
    for key in FUNDAMENTAL_INFO_KEYS:
        value = info.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        useful_count += 1
        if useful_count >= 2:
            return True
    return False


def _ticker_info_dict(ticker: Any, method: str) -> dict[str, Any]:
    try:
        if method == "get_info":
            info = ticker.get_info()
        else:
            info = ticker.info
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


def get_info(symbol: str) -> dict[str, Any]:
    """Robust yfinance fundamentals retrieval without session/json fallback.

    For each scan this function uses only live data from the current run:
    1. try Ticker.get_info();
    2. if the response is empty/useless, try Ticker.info;
    3. retry a few times with a small delay.

    No previous session data and no JSON cache are used.
    """
    symbol = str(symbol or "").strip()
    if not symbol:
        return {}
    attempts = max(1, GET_INFO_RETRY_COUNT)
    for attempt in range(attempts):
        ticker = yf.Ticker(symbol)
        for method in ("get_info", "info"):
            info = _ticker_info_dict(ticker, method)
            if info_has_useful_fundamentals(info):
                return info
        if attempt < attempts - 1:
            time.sleep(GET_INFO_RETRY_SLEEP_SECONDS * (attempt + 1))
    return {}


def get_info_value(info: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = info.get(key)
        if value is not None:
            return value
    return None


def pct_from_ratio(value: Any) -> float | None:
    v = safe_float(value)
    return None if v is None else v * 100


def tv_chart_url(tv_symbol: str) -> str:
    encoded = urllib.parse.quote(str(tv_symbol or "").strip(), safe="")
    return f"https://www.tradingview.com/chart/?symbol={encoded}" if encoded else ""


def hist_gap(dist_pct: Any, hist_min_pct: Any) -> float | None:
    d = safe_float(dist_pct)
    h = safe_float(hist_min_pct)
    return None if d is None or h is None else abs(d - h)


def below_sma(dist_pct: Any) -> bool:
    d = safe_float(dist_pct)
    return bool(d is not None and d < 0)


def orange_zone(dist_pct: Any, hist_min_pct: Any) -> bool:
    d = safe_float(dist_pct)
    if d is None or d >= SMA200_HIST_MIN_DIST_LIMIT:
        return False
    gap = hist_gap(d, hist_min_pct)
    return bool(gap is not None and gap <= SMA200_HIST_MIN_PROXIMITY_POINTS)


def equivalent_price(sma: Any, pct_value: Any) -> float | None:
    s = safe_float(sma)
    p = safe_float(pct_value)
    if s is None or s <= 0 or p is None:
        return None
    return s * (1 + p / 100)


FIB_LEVELS = (0.500, 0.618, 0.786, 0.887)


def fib_level_price(low: float, high: float, ratio: float) -> float:
    return high - (high - low) * ratio


def compute_fibonacci_w(weekly: pd.DataFrame, sma200_series: pd.Series, current_price: Any) -> dict[str, Any]:
    """Automatic weekly Fibonacci from last cycle below SMA200W to next weekly high.

    Rule used:
    - find all weekly periods where Low is below SMA200W;
    - take the most recent contiguous period below SMA200W;
    - swing low = lowest Low of that period;
    - swing high = highest High after the swing low.
    """
    result: dict[str, Any] = {
        "fib_available": False,
        "fib_error": "",
        "fib_low": None,
        "fib_low_date": None,
        "fib_high": None,
        "fib_high_date": None,
        "fib_0500": None,
        "fib_0618": None,
        "fib_0786": None,
        "fib_0887": None,
        "fib_first_buy_low": None,
        "fib_first_buy_high": None,
        "fib_buy_low": None,
        "fib_buy_high": None,
        "fib_strong_low": None,
        "fib_strong_high": None,
        "fib_status": "dati insufficienti",
    }
    try:
        if weekly is None or weekly.empty or "Low" not in weekly.columns or "High" not in weekly.columns:
            result["fib_error"] = "weekly Low/High mancanti"
            return result
        hist = weekly.copy()
        hist["SMA200W"] = sma200_series
        hist = hist.dropna(subset=["Low", "High", "SMA200W"])
        hist = hist[(hist["Low"] > 0) & (hist["High"] > 0) & (hist["SMA200W"] > 0)]
        below_mask = hist["Low"] < hist["SMA200W"]
        if not bool(below_mask.any()):
            result["fib_error"] = "nessun ciclo sotto SMA200W"
            return result

        # Most recent contiguous block where Low < SMA200W.
        below_positions = [idx for idx, flag in enumerate(below_mask.tolist()) if flag]
        last_pos = below_positions[-1]
        start_pos = last_pos
        while start_pos > 0 and bool(below_mask.iloc[start_pos - 1]):
            start_pos -= 1
        cycle = hist.iloc[start_pos:last_pos + 1]
        if cycle.empty:
            result["fib_error"] = "ciclo sotto SMA200W vuoto"
            return result

        low_idx = cycle["Low"].astype(float).idxmin()
        low_value = safe_float(cycle.loc[low_idx, "Low"])
        if low_value is None:
            result["fib_error"] = "minimo ciclo non valido"
            return result

        after_low = hist.loc[low_idx:]
        if after_low.empty:
            result["fib_error"] = "nessun massimo successivo"
            return result
        high_idx = after_low["High"].astype(float).idxmax()
        high_value = safe_float(after_low.loc[high_idx, "High"])
        if high_value is None or high_value <= low_value:
            result["fib_error"] = "massimo successivo non valido"
            return result

        levels = {ratio: fib_level_price(low_value, high_value, ratio) for ratio in FIB_LEVELS}
        p = safe_float(current_price)
        fib_0500 = levels[0.500]
        fib_0618 = levels[0.618]
        fib_0786 = levels[0.786]
        fib_0887 = levels[0.887]

        status = "fuori area"
        if p is not None:
            if fib_0618 <= p <= fib_0500:
                status = "Fib First Buy Area"
            elif fib_0786 <= p < fib_0618:
                status = "Fib Buy Area"
            elif fib_0887 <= p < fib_0786:
                status = "Fib Strong Buy Area"
            elif p > fib_0500:
                status = f"Fuori area · prezzo sopra 0.500 ({fmt_price(fib_0500)})"
            elif p < fib_0887:
                status = f"Sotto Fib Strong · prezzo sotto 0.887 ({fmt_price(fib_0887)})"

        def date_text(idx: Any) -> str:
            return idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)

        result.update({
            "fib_available": True,
            "fib_low": low_value,
            "fib_low_date": date_text(low_idx),
            "fib_high": high_value,
            "fib_high_date": date_text(high_idx),
            "fib_0500": fib_0500,
            "fib_0618": fib_0618,
            "fib_0786": fib_0786,
            "fib_0887": fib_0887,
            "fib_first_buy_low": fib_0618,
            "fib_first_buy_high": fib_0500,
            "fib_buy_low": fib_0786,
            "fib_buy_high": fib_0618,
            "fib_strong_low": fib_0887,
            "fib_strong_high": fib_0786,
            "fib_status": status,
        })
        return result
    except Exception as exc:
        result["fib_error"] = str(exc)
        return result


def quote_data(symbol: str) -> dict[str, Any]:
    last_price = previous_close = None
    currency = ""
    try:
        intraday = normalize_df(yf_download(symbol, period="5d", interval="15m", auto_adjust=False))
        if not intraday.empty and "Close" in intraday.columns:
            intraday = intraday.dropna(subset=["Close"])
            if not intraday.empty:
                last_price = safe_float(intraday["Close"].iloc[-1])
    except Exception:
        pass
    try:
        daily = normalize_df(yf_download(symbol, period="10d", interval="1d", auto_adjust=False))
        if not daily.empty and "Close" in daily.columns:
            daily = daily.dropna(subset=["Close"])
            if last_price is None and not daily.empty:
                last_price = safe_float(daily["Close"].iloc[-1])
            if len(daily) >= 2:
                previous_close = safe_float(daily["Close"].iloc[-2])
            elif len(daily) == 1:
                previous_close = safe_float(daily["Close"].iloc[-1])
    except Exception:
        pass
    try:
        fast = yf.Ticker(symbol).fast_info
        currency = str(fast.get("currency") or "").upper()
        if last_price is None:
            last_price = safe_float(fast.get("last_price") or fast.get("lastPrice"))
        if previous_close is None:
            previous_close = safe_float(fast.get("previous_close") or fast.get("previousClose"))
    except Exception:
        pass
    daily_change_pct = None
    if last_price is not None and previous_close not in (None, 0):
        daily_change_pct = ((last_price - previous_close) / previous_close) * 100
    return {"last_price": last_price, "previous_close": previous_close, "daily_change_pct": daily_change_pct, "currency": currency}


def technical_metrics(item: dict[str, str]) -> dict[str, Any]:
    symbol = item["yahoo"]
    row: dict[str, Any] = {
        "ticker": item["ticker"], "yahoo": symbol, "tv": item.get("tv", ""), "name": item.get("name", ""),
        "last_price": None, "previous_close": None, "daily_change_pct": None, "currency": "",
        "sma200w": None, "dist_pct": None, "hist_min_w_pct": None, "hist_min_w_date": None, "hist_min_w_low": None, "hist_min_equivalent": None,
        "hist_max_w_pct": None, "hist_max_w_date": None, "hist_max_w_high": None, "hist_max_equivalent": None,
        "gap_points": None, "below_sma200w": False, "orange_zone": False,
        "momentum_26w_pct": None, "momentum_52w_pct": None, "drawdown_52w_pct": None, "weekly_vol_52w_pct": None,
        "error": "",
    }
    try:
        row.update(quote_data(symbol))
        weekly = normalize_df(yf_download(symbol, period="20y", interval="1wk", auto_adjust=False))
        if weekly.empty or "Close" not in weekly.columns:
            row["error"] = "weekly vuoto o Close mancante"
            return row
        weekly = weekly.dropna(subset=["Close"])
        if len(weekly) < SMA_WEEKS:
            row["error"] = f"storico insufficiente: {len(weekly)} settimane"
            return row
        close = weekly["Close"].astype(float)
        sma200_series = close.rolling(SMA_WEEKS).mean()
        sma200 = safe_float(sma200_series.iloc[-1])
        row["sma200w"] = sma200
        if sma200 and row["last_price"] is not None:
            row["dist_pct"] = ((row["last_price"] - sma200) / sma200) * 100
        if len(close) >= 27:
            row["momentum_26w_pct"] = ((close.iloc[-1] / close.iloc[-27]) - 1) * 100
        if len(close) >= 53:
            row["momentum_52w_pct"] = ((close.iloc[-1] / close.iloc[-53]) - 1) * 100
        high_52 = safe_float(close.tail(52).max())
        if high_52 and high_52 > 0:
            row["drawdown_52w_pct"] = ((close.iloc[-1] / high_52) - 1) * 100
        returns = close.pct_change().tail(52).dropna()
        if not returns.empty:
            row["weekly_vol_52w_pct"] = float(returns.std() * 100)
        if "Low" in weekly.columns and "High" in weekly.columns:
            hist = weekly.copy()
            hist["SMA200W"] = sma200_series
            hist = hist.dropna(subset=["Low", "High", "SMA200W"])
            hist = hist[(hist["Low"] > 0) & (hist["High"] > 0) & (hist["SMA200W"] > 0)]
            below = hist[hist["Low"] < hist["SMA200W"]]
            if not below.empty:
                dd = ((below["SMA200W"] - below["Low"]) / below["SMA200W"]) * 100
                min_idx = dd.idxmax()
                row["hist_min_w_pct"] = -safe_float(dd.max())
                row["hist_min_w_date"] = min_idx.strftime("%Y-%m-%d") if hasattr(min_idx, "strftime") else str(min_idx)
                row["hist_min_w_low"] = safe_float(below.loc[min_idx].get("Low"))
                row["hist_min_equivalent"] = equivalent_price(sma200, row["hist_min_w_pct"])
            above = hist[hist["High"] > hist["SMA200W"]]
            if not above.empty:
                mx = ((above["High"] - above["SMA200W"]) / above["SMA200W"]) * 100
                max_idx = mx.idxmax()
                row["hist_max_w_pct"] = safe_float(mx.max())
                row["hist_max_w_date"] = max_idx.strftime("%Y-%m-%d") if hasattr(max_idx, "strftime") else str(max_idx)
                row["hist_max_w_high"] = safe_float(above.loc[max_idx].get("High"))
                row["hist_max_equivalent"] = equivalent_price(sma200, row["hist_max_w_pct"])
        row["gap_points"] = hist_gap(row["dist_pct"], row["hist_min_w_pct"])
        row["below_sma200w"] = below_sma(row["dist_pct"])
        row["orange_zone"] = orange_zone(row["dist_pct"], row["hist_min_w_pct"])
        row.update(compute_fibonacci_w(weekly, sma200_series, row.get("last_price")))
        return row
    except Exception as exc:
        row["error"] = str(exc)
        return row


def fundamentals(symbol: str, last_price: Any) -> dict[str, Any]:
    out = {key: None for key in [
        "market_cap", "forward_pe", "trailing_pe", "peg_ratio", "price_to_sales", "free_cashflow",
        "fcf_yield_pct", "return_on_equity_pct", "gross_margin_pct", "operating_margin_pct",
        "profit_margin_pct", "debt_to_equity", "revenue_growth_pct", "earnings_growth_pct",
        "beta", "target_mean_price", "target_upside_pct", "recommendation_mean",
    ]}
    out["info_error"] = ""
    try:
        info = get_info(symbol)
        if not info:
            out["info_error"] = "fondamentali yfinance non disponibili dopo retry live"
        out["market_cap"] = safe_float(get_info_value(info, "marketCap"))
        out["forward_pe"] = safe_float(get_info_value(info, "forwardPE"))
        out["trailing_pe"] = safe_float(get_info_value(info, "trailingPE"))
        out["peg_ratio"] = safe_float(get_info_value(info, "pegRatio", "trailingPegRatio"))
        out["price_to_sales"] = safe_float(get_info_value(info, "priceToSalesTrailing12Months"))
        out["free_cashflow"] = safe_float(get_info_value(info, "freeCashflow"))
        out["return_on_equity_pct"] = pct_from_ratio(get_info_value(info, "returnOnEquity"))
        out["gross_margin_pct"] = pct_from_ratio(get_info_value(info, "grossMargins"))
        out["operating_margin_pct"] = pct_from_ratio(get_info_value(info, "operatingMargins"))
        out["profit_margin_pct"] = pct_from_ratio(get_info_value(info, "profitMargins"))
        out["debt_to_equity"] = safe_float(get_info_value(info, "debtToEquity"))
        out["revenue_growth_pct"] = pct_from_ratio(get_info_value(info, "revenueGrowth"))
        out["earnings_growth_pct"] = pct_from_ratio(get_info_value(info, "earningsGrowth"))
        out["beta"] = safe_float(get_info_value(info, "beta"))
        out["target_mean_price"] = safe_float(get_info_value(info, "targetMeanPrice"))
        out["recommendation_mean"] = safe_float(get_info_value(info, "recommendationMean"))
        if out["market_cap"] and out["free_cashflow"] is not None:
            out["fcf_yield_pct"] = (out["free_cashflow"] / out["market_cap"]) * 100
        price = safe_float(last_price)
        if out["target_mean_price"] is not None and price:
            out["target_upside_pct"] = ((out["target_mean_price"] - price) / price) * 100
    except Exception as exc:
        out["info_error"] = str(exc)
    return out


def score_technical(row: dict[str, Any]) -> tuple[float, list[str]]:
    notes, score = [], 0.0
    dist, gap = safe_float(row.get("dist_pct")), safe_float(row.get("gap_points"))
    if row.get("orange_zone"):
        score += 15; notes.append("area arancione")
    elif row.get("below_sma200w"):
        score += 8; notes.append("sotto SMA200W")
    elif dist is not None and dist < 10:
        score += 4; notes.append("vicino SMA200W")
    if gap is not None:
        score += clip(10 - gap, 0, 10)
        if gap <= 5:
            notes.append("scarto storico stretto")
    return round(clip(score, 0, 25), 1), notes


def score_valuation(f: dict[str, Any]) -> tuple[float, list[str]]:
    notes, score = [], 0.0
    fpe, peg, fcfy, ps, tgt = [safe_float(f.get(k)) for k in ["forward_pe", "peg_ratio", "fcf_yield_pct", "price_to_sales", "target_upside_pct"]]
    if fpe is not None:
        score += 5 if fpe <= 15 else 4 if fpe <= 25 else 2 if fpe <= 35 else 0
        if fpe <= 25: notes.append("FwdPE ok/basso")
    if peg is not None:
        score += 4 if peg <= 1.2 else 2 if peg <= 2.0 else 0
        if peg <= 1.2: notes.append("PEG buono")
    if fcfy is not None:
        score += 5 if fcfy >= 5 else 3 if fcfy >= 3 else 1 if fcfy > 0 else 0
        if fcfy >= 3: notes.append("FCF yield ok")
    if ps is not None:
        score += 3 if ps <= 5 else 1 if ps <= 10 else 0
    if tgt is not None:
        score += 3 if tgt >= 15 else 1 if tgt >= 5 else 0
        if tgt >= 15: notes.append("upside target")
    return round(clip(score, 0, 20), 1), notes


def score_quality(f: dict[str, Any]) -> tuple[float, list[str]]:
    notes, score = [], 0.0
    roe, opm, pm, gm, dte, fcf = [safe_float(f.get(k)) for k in ["return_on_equity_pct", "operating_margin_pct", "profit_margin_pct", "gross_margin_pct", "debt_to_equity", "free_cashflow"]]
    if roe is not None:
        score += 5 if roe >= 25 else 3 if roe >= 15 else 0
        if roe >= 25: notes.append("ROE alto")
    if opm is not None:
        score += 5 if opm >= 25 else 3 if opm >= 15 else 0
        if opm >= 25: notes.append("margine operativo alto")
    if pm is not None: score += 4 if pm >= 20 else 2 if pm >= 10 else 0
    if gm is not None: score += 3 if gm >= 50 else 2 if gm >= 35 else 0
    if dte is not None: score += 2 if dte <= 80 else 1 if dte <= 150 else 0
    if fcf is not None and fcf > 0: score += 1; notes.append("FCF positivo")
    return round(clip(score, 0, 20), 1), notes


def score_growth(f: dict[str, Any]) -> tuple[float, list[str]]:
    notes, score = [], 0.0
    rev, earn, rec, tgt = [safe_float(f.get(k)) for k in ["revenue_growth_pct", "earnings_growth_pct", "recommendation_mean", "target_upside_pct"]]
    if rev is not None:
        score += 5 if rev >= 15 else 3 if rev >= 5 else 1 if rev >= 0 else 0
        if rev >= 15: notes.append("ricavi in crescita")
    if earn is not None:
        score += 5 if earn >= 15 else 3 if earn >= 5 else 1 if earn >= 0 else 0
        if earn >= 15: notes.append("utili in crescita")
    if rec is not None:
        score += 3 if rec <= 2.0 else 2 if rec <= 2.7 else 0
        if rec <= 2.0: notes.append("analyst rating buono")
    if tgt is not None and tgt > 0: score += 2
    return round(clip(score, 0, 15), 1), notes


def score_risk_momentum(row: dict[str, Any], f: dict[str, Any]) -> tuple[float, list[str]]:
    notes, score = [], 0.0
    beta, mom26, mom52, dd52, vol = [safe_float(x) for x in [f.get("beta"), row.get("momentum_26w_pct"), row.get("momentum_52w_pct"), row.get("drawdown_52w_pct"), row.get("weekly_vol_52w_pct")]]
    if beta is not None:
        score += 4 if beta <= 1.0 else 3 if beta <= 1.3 else 1 if beta <= 1.7 else 0
        if beta <= 1.0: notes.append("beta difensivo")
    if mom26 is not None:
        score += 4 if mom26 > 10 else 3 if mom26 > 0 else 1 if mom26 > -10 else 0
        if mom26 > 10: notes.append("momentum 6m positivo")
    if mom52 is not None: score += 3 if mom52 > 10 else 2 if mom52 > 0 else 1 if mom52 > -15 else 0
    if dd52 is not None: score += 4 if dd52 > -10 else 2 if dd52 > -25 else 1 if dd52 > -40 else 0
    if vol is not None:
        score += 5 if vol <= 3 else 3 if vol <= 5 else 1 if vol <= 8 else 0
        if vol <= 3: notes.append("volatilità bassa")
    return round(clip(score, 0, 20), 1), notes


def institutional_label(score: float) -> str:
    if score >= STRONG_BUY_ZONE_THRESHOLD: return "Strong Buy Zone"
    if score >= BUY_ZONE_THRESHOLD: return "Buy Zone"
    if score >= 50: return "Watch"
    return "Monitor"


def compute_score(row: dict[str, Any], f: dict[str, Any]) -> dict[str, Any]:
    buckets = [score_technical(row), score_valuation(f), score_quality(f), score_growth(f), score_risk_momentum(row, f)]
    total = round(sum(bucket[0] for bucket in buckets), 1)
    notes: list[str] = []
    for _, bucket_notes in buckets:
        notes.extend(bucket_notes[:2])
    return {
        "score_total": total,
        "score_label": institutional_label(total),
        "score_technical": buckets[0][0],
        "score_valuation": buckets[1][0],
        "score_quality": buckets[2][0],
        "score_growth": buckets[3][0],
        "score_risk_momentum": buckets[4][0],
        "score_notes": "; ".join(notes[:8]),
    }


def data_quality(fund: dict[str, Any]) -> dict[str, Any]:
    missing_groups, missing_fields = [], []
    present_fields = total_fields = 0
    for group, fields in FUNDAMENTAL_FIELDS.items():
        group_present = 0
        for field in fields:
            total_fields += 1
            if safe_float(fund.get(field)) is not None:
                present_fields += 1
                group_present += 1
            else:
                missing_fields.append(field)
        if group_present == 0:
            missing_groups.append(group)
    ratio = present_fields / total_fields if total_fields else 0.0
    label = "Dati completi" if ratio >= 0.80 else "Dati parziali" if ratio > 0 else "Fondamentali assenti"
    return {
        "data_complete": ratio >= 0.80,
        "data_partial": ratio > 0 and ratio < 0.80,
        "data_quality_ratio": round(ratio, 3),
        "data_quality_label": label,
        "data_missing_groups": missing_groups,
        "data_missing_fields": missing_fields,
    }


def simulate_at_price(record: dict[str, Any], price: float) -> dict[str, Any]:
    sim = dict(record)
    current = safe_float(record.get("last_price"))
    if current is None or current <= 0 or price <= 0:
        return sim
    ratio = price / current
    sim["last_price"] = price
    sma = safe_float(sim.get("sma200w"))
    if sma and sma > 0:
        sim["dist_pct"] = ((price - sma) / sma) * 100
    sim["gap_points"] = hist_gap(sim.get("dist_pct"), sim.get("hist_min_w_pct"))
    sim["below_sma200w"] = below_sma(sim.get("dist_pct"))
    sim["orange_zone"] = orange_zone(sim.get("dist_pct"), sim.get("hist_min_w_pct"))
    for key in ("forward_pe", "trailing_pe", "price_to_sales"):
        value = safe_float(record.get(key))
        if value is not None:
            sim[key] = value * ratio
    fcfy = safe_float(record.get("fcf_yield_pct"))
    if fcfy is not None and ratio > 0:
        sim["fcf_yield_pct"] = fcfy / ratio
    target = safe_float(record.get("target_mean_price"))
    if target is not None:
        sim["target_upside_pct"] = ((target - price) / price) * 100
    sim.update(compute_score(sim, sim))
    return sim


def find_zone_range(record: dict[str, Any], threshold: float) -> dict[str, Any]:
    current = safe_float(record.get("last_price"))
    if current is None or current <= 0:
        return {"status": "not_enough_data", "low": None, "high": None, "active": False, "threshold": threshold, "max_score": None, "max_score_orange": None}

    valid: list[float] = []
    max_score_any: float | None = None
    max_score_orange: float | None = None

    for i in range(int((MAX_SIMULATED_DISCOUNT_PCT * 2) / SIMULATION_STEP_PCT) + 1):
        pct = -MAX_SIMULATED_DISCOUNT_PCT + i * SIMULATION_STEP_PCT
        price = current * (1 + pct / 100)
        if price <= 0:
            continue
        sim = simulate_at_price(record, price)
        sim_score = safe_float(sim.get("score_total"))
        if sim_score is not None:
            max_score_any = sim_score if max_score_any is None else max(max_score_any, sim_score)
        if bool(sim.get("orange_zone")):
            if sim_score is not None:
                max_score_orange = sim_score if max_score_orange is None else max(max_score_orange, sim_score)
            if (sim_score or 0) >= threshold:
                valid.append(price)

    if not valid:
        return {"status": "threshold_not_reached", "low": None, "high": None, "active": False, "threshold": threshold, "max_score": max_score_any, "max_score_orange": max_score_orange}

    active = bool(record.get("orange_zone")) and (safe_float(record.get("score_total")) or 0) >= threshold
    return {"status": "range", "low": min(valid), "high": max(valid), "active": active, "threshold": threshold, "max_score": max_score_any, "max_score_orange": max_score_orange}


def median_value(values: list[float]) -> float | None:
    cleaned = sorted(v for v in values if safe_float(v) is not None and float(v) > 0)
    if not cleaned:
        return None
    n = len(cleaned)
    mid = n // 2
    return cleaned[mid] if n % 2 else (cleaned[mid - 1] + cleaned[mid]) / 2


def fair_value_model(record: dict[str, Any]) -> dict[str, Any]:
    """Conservative fair-value model for the Institutional Buy Zone V1."""
    current = safe_float(record.get("last_price"))
    quality = safe_float(record.get("score_quality")) or 0.0
    growth = safe_float(record.get("score_growth")) or 0.0
    beta = safe_float(record.get("beta"))
    candidates: list[float] = []
    methods: list[str] = []

    fwd_pe = safe_float(record.get("forward_pe"))
    if current is not None and current > 0 and fwd_pe is not None and fwd_pe > 0:
        target_pe = 10.0 + (clip(quality, 0, 20) / 20.0) * 2.0 + (clip(growth, 0, 15) / 15.0) * 2.0
        target_pe = clip(target_pe, 10.0, 14.5)
        fv_pe = (current / fwd_pe) * target_pe
        if fv_pe > 0:
            candidates.append(fv_pe)
            methods.append("Fwd P/E")

    fcf_yield = safe_float(record.get("fcf_yield_pct"))
    if current is not None and current > 0 and fcf_yield is not None and fcf_yield > 0:
        required_fcf_yield = 11.0 - (clip(quality, 0, 20) / 20.0) * 2.0 - (clip(growth, 0, 15) / 15.0) * 1.0
        required_fcf_yield = clip(required_fcf_yield, 8.0, 12.0)
        fv_fcf = current * (fcf_yield / required_fcf_yield)
        if fv_fcf > 0:
            candidates.append(fv_fcf)
            methods.append("FCF Yield")

    target_mean = safe_float(record.get("target_mean_price"))
    if target_mean is not None and target_mean > 0:
        fv_target = target_mean * 0.80
        if fv_target > 0:
            candidates.append(fv_target)
            methods.append("Target analisti 80%")

    fair_value = median_value(candidates)
    margin = None
    fundamental_buy_price = None
    if fair_value is not None:
        if quality >= 15:
            margin = 22.0
        elif quality >= 11:
            margin = 25.0
        else:
            margin = 30.0
        if beta is not None:
            if beta >= 1.50:
                margin += 5.0
            elif beta >= 1.20:
                margin += 3.0
        if growth >= 12:
            margin -= 2.0
        elif growth < 6:
            margin += 3.0
        if not bool(record.get("data_complete")):
            margin += 5.0
        margin = clip(margin, 20.0, 40.0)
        fundamental_buy_price = fair_value * (1 - margin / 100.0)

    upside = None
    if current is not None and current > 0 and fair_value is not None:
        upside = (fair_value / current - 1) * 100.0

    return {
        "fair_value_composite": round(fair_value, 2) if fair_value is not None else None,
        "fair_value_methods": methods,
        "required_margin_safety_pct": round(margin, 1) if margin is not None else None,
        "fundamental_buy_price": round(fundamental_buy_price, 2) if fundamental_buy_price is not None else None,
        "upside_to_fair_value_pct": round(upside, 1) if upside is not None else None,
    }


def institutional_buy_zone_model(record: dict[str, Any]) -> dict[str, Any]:
    """Buy Zone = Eq oggi MinW -> SMA200W."""
    low = safe_float(record.get("hist_min_equivalent"))
    high = safe_float(record.get("sma200w"))
    current = safe_float(record.get("last_price"))
    if low is None or low <= 0 or high is None or high <= 0:
        return {"status": "not_enough_data", "low": low, "high": high, "active": False}
    if high < low:
        low, high = high, low
    active = bool(current is not None and low <= current <= high)
    if current is None:
        position = "N/D"
    elif current < low:
        position = "sotto la zona"
    elif current > high:
        position = "sopra la zona"
    else:
        position = "dentro la zona"
    return {"status": "range", "low": low, "high": high, "active": active, "position": position}


def format_institutional_buy_zone(record: dict[str, Any]) -> str:
    data = record.get("institutional_buy_zone")
    currency = str(record.get("currency") or "").upper()
    if not isinstance(data, dict):
        return "dati insufficienti"
    if data.get("status") == "range":
        prefix = "attiva · " if data.get("active") else ""
        return prefix + fmt_price(data.get("low"), currency) + " - " + fmt_price(data.get("high"), currency)
    return "dati insufficienti"


def format_institutional_buy_zone_status(record: dict[str, Any]) -> str:
    data = record.get("institutional_buy_zone")
    if not isinstance(data, dict):
        return "N/D"
    if data.get("status") == "range":
        return str(data.get("position") or "N/D")
    return "dati insufficienti"


def institutional_display_label(record: dict[str, Any]) -> str:
    zone = record.get("institutional_buy_zone")
    if isinstance(zone, dict) and zone.get("active"):
        return "Buy Zone"
    if bool(record.get("orange_zone")):
        return "Technical Stress"
    score = safe_float(record.get("score_total")) or 0.0
    if score >= BUY_ZONE_THRESHOLD:
        return "Fundamental Watch"
    if score >= 50:
        return "Watch"
    return "Monitor"


def format_zone_range(record: dict[str, Any], key: str) -> str:
    data = record.get(key)
    currency = str(record.get("currency") or "").upper()
    if not isinstance(data, dict):
        return "dati insufficienti"
    status = data.get("status")
    threshold = safe_float(data.get("threshold"))
    if status == "range":
        return ("attiva · " if data.get("active") else "") + fmt_price(data.get("low"), currency) + " - " + fmt_price(data.get("high"), currency)
    if status == "not_enough_data":
        return "dati insufficienti"
    if status == "threshold_not_reached":
        max_score = safe_float(data.get("max_score_orange"))
        if max_score is None:
            max_score = safe_float(data.get("max_score"))
        threshold_text = fmt_num(threshold, 0) if threshold is not None else "N/D"
        max_text = fmt_num(max_score, 1) if max_score is not None else "N/D"
        return f"Soglia {threshold_text} non raggiunta · Max simulato: {max_text} / {threshold_text}"
    return "dati insufficienti"


def build_record(item: dict[str, str]) -> dict[str, Any]:
    tech = technical_metrics(item)
    fund = fundamentals(tech.get("yahoo", item.get("yahoo", "")), tech.get("last_price"))
    quality = data_quality(fund)
    score = compute_score(tech, fund)
    record: dict[str, Any] = {}
    record.update(tech)
    record.update(fund)
    record.update(quality)
    record.update(score)
    record["institutional_buy_zone"] = institutional_buy_zone_model(record)
    record["institutional_buy_zone_text"] = format_institutional_buy_zone(record)
    record["institutional_buy_zone_status_text"] = format_institutional_buy_zone_status(record)
    record["display_label"] = institutional_display_label(record)
    record["tradingview_url"] = tv_chart_url(str(record.get("tv") or item.get("tv") or ""))
    return record


def sort_priority(record: dict[str, Any]) -> tuple[int, float, str]:
    score = safe_float(record.get("score_total")) or 0
    label = str(record.get("display_label") or "")
    if label == "Institutional Buy Zone":
        group = 0
    elif label == "Technical Stress":
        group = 1
    elif label == "Fundamental Watch":
        group = 2
    elif score >= 50:
        group = 3
    else:
        group = 4
    return (group, -score, str(record.get("ticker") or ""))


def scan_symbols(limit: int | None = None) -> list[dict[str, Any]]:
    symbols = SYMBOLS[:limit] if limit else SYMBOLS
    records: list[dict[str, Any]] = []
    for idx, item in enumerate(symbols, 1):
        records.append(build_record(item))
        if idx < len(symbols) and SLEEP_BETWEEN_TICKERS_SECONDS > 0:
            time.sleep(SLEEP_BETWEEN_TICKERS_SECONDS)
    return sorted(records, key=sort_priority)


def scan_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    top = max(records, key=lambda r: safe_float(r.get("score_total")) or -1, default={})
    institutional_count = len([r for r in records if str(r.get("display_label") or "") == "Buy Zone"])
    technical_stress_count = len([r for r in records if str(r.get("display_label") or "") == "Technical Stress"])
    return {
        "count": len(records),
        "top_ticker": top.get("ticker", "-"),
        "top_score": top.get("score_total"),
        "buy_strong_count": len([r for r in records if (safe_float(r.get("score_total")) or 0) >= BUY_ZONE_THRESHOLD]),
        "buy_zone_count": institutional_count,
        "institutional_count": institutional_count,
        "technical_stress_count": technical_stress_count,
        "orange_count": len([r for r in records if bool(r.get("orange_zone"))]),
        "partial_count": len([r for r in records if not r.get("data_complete", False)]),
        "errors_count": len([r for r in records if str(r.get("error") or "").strip()]),
        "last_update": now_rome().strftime("%d/%m/%Y %H:%M:%S"),
    }
