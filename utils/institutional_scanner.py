
from __future__ import annotations

import math
import os
import time
import urllib.parse
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

TIMEZONE = ZoneInfo("Europe/Rome")
SMA_WEEKS = 200
LINREG_WEEKS = int(os.getenv("INSTITUTIONAL_LINREG_WEEKS", "200"))
LINREG_STD_MULT = float(os.getenv("INSTITUTIONAL_LINREG_STD_MULT", "2.0"))
LINREG_NEAR_LOWER_PCT = float(os.getenv("INSTITUTIONAL_LINREG_NEAR_LOWER_PCT", "5.0"))
SMA200_HIST_MIN_PROXIMITY_POINTS = float(os.getenv("INSTITUTIONAL_MIN_GAP_POINTS", "10.0"))
SMA200_HIST_MIN_DIST_LIMIT = 0.0
SLEEP_BETWEEN_TICKERS_SECONDS = float(os.getenv("INSTITUTIONAL_SCANNER_SLEEP", "0.35"))
YF_REPAIR = os.getenv("YF_REPAIR", "false").strip().lower() in {"1", "true", "yes", "y"}
SYMBOLS = [{'ticker': 'TSLA', 'yahoo': 'TSLA', 'tv': 'NASDAQ:TSLA', 'name': 'Tesla'}, {'ticker': 'COST', 'yahoo': 'COST', 'tv': 'NASDAQ:COST', 'name': 'Costco'}, {'ticker': 'MSFT', 'yahoo': 'MSFT', 'tv': 'NASDAQ:MSFT', 'name': 'Microsoft'}, {'ticker': 'V', 'yahoo': 'V', 'tv': 'NYSE:V', 'name': 'Visa'}, {'ticker': 'MA', 'yahoo': 'MA', 'tv': 'NYSE:MA', 'name': 'Mastercard'}, {'ticker': 'ORCL', 'yahoo': 'ORCL', 'tv': 'NYSE:ORCL', 'name': 'Oracle'}, {'ticker': 'PG', 'yahoo': 'PG', 'tv': 'NYSE:PG', 'name': 'Procter & Gamble'}, {'ticker': 'JNJ', 'yahoo': 'JNJ', 'tv': 'NYSE:JNJ', 'name': 'Johnson & Johnson'}, {'ticker': 'KO', 'yahoo': 'KO', 'tv': 'NYSE:KO', 'name': 'Coca-Cola'}, {'ticker': 'PEP', 'yahoo': 'PEP', 'tv': 'NASDAQ:PEP', 'name': 'PepsiCo'}, {'ticker': 'MCD', 'yahoo': 'MCD', 'tv': 'NYSE:MCD', 'name': "McDonald's"}, {'ticker': 'ABT', 'yahoo': 'ABT', 'tv': 'NYSE:ABT', 'name': 'Abbott Laboratories'}, {'ticker': 'WMT', 'yahoo': 'WMT', 'tv': 'NYSE:WMT', 'name': 'Walmart'}, {'ticker': 'AAPL', 'yahoo': 'AAPL', 'tv': 'NASDAQ:AAPL', 'name': 'Apple'}, {'ticker': 'GOOG', 'yahoo': 'GOOG', 'tv': 'NASDAQ:GOOG', 'name': 'Alphabet Class C'}, {'ticker': 'BRK.B', 'yahoo': 'BRK-B', 'tv': 'NYSE:BRK.B', 'name': 'Berkshire Hathaway'}, {'ticker': 'NVDA', 'yahoo': 'NVDA', 'tv': 'NASDAQ:NVDA', 'name': 'NVIDIA'}, {'ticker': 'ASML', 'yahoo': 'ASML', 'tv': 'NASDAQ:ASML', 'name': 'ASML Holding'}, {'ticker': 'META', 'yahoo': 'META', 'tv': 'NASDAQ:META', 'name': 'Meta Platforms'}, {'ticker': 'IBM', 'yahoo': 'IBM', 'tv': 'NYSE:IBM', 'name': 'IBM'}, {'ticker': 'AVGO', 'yahoo': 'AVGO', 'tv': 'NASDAQ:AVGO', 'name': 'Broadcom'}, {'ticker': 'AXP', 'yahoo': 'AXP', 'tv': 'NYSE:AXP', 'name': 'American Express'}, {'ticker': 'AMZN', 'yahoo': 'AMZN', 'tv': 'NASDAQ:AMZN', 'name': 'Amazon'}, {'ticker': 'CRM', 'yahoo': 'CRM', 'tv': 'NYSE:CRM', 'name': 'Salesforce'}]


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


def quote_data(symbol: str) -> dict[str, Any]:
    last_price = previous_close = None
    currency = ""
    try:
        daily = normalize_df(yf_download(symbol, period="10d", interval="1d", auto_adjust=False))
        if not daily.empty and "Close" in daily.columns:
            daily = daily.dropna(subset=["Close"])
            if not daily.empty:
                last_price = safe_float(daily["Close"].iloc[-1])
            if len(daily) >= 2:
                previous_close = safe_float(daily["Close"].iloc[-2])
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


def compute_linreg_w(close: pd.Series, current_price: Any) -> dict[str, Any]:
    out = {
        "linreg_available": False,
        "linreg_error": "",
        "linreg_mid_w": None,
        "linreg_lower_w": None,
        "linreg_upper_w": None,
        "linreg_dist_lower_pct": None,
        "linreg_position_pct": None,
    }
    try:
        series = close.dropna().astype(float)
        series = series[series > 0]
        if len(series) < LINREG_WEEKS:
            out["linreg_error"] = f"storico linreg insufficiente: {len(series)} settimane"
            return out
        window = series.iloc[-LINREG_WEEKS:]
        y = window.apply(math.log)
        n = len(y)
        x = list(range(n))
        sx = sum(x)
        sy = float(y.sum())
        sxx = sum(i * i for i in x)
        sxy = sum(i * float(v) for i, v in zip(x, y))
        denom = n * sxx - sx * sx
        if denom == 0:
            out["linreg_error"] = "denominatore linreg nullo"
            return out
        slope = (n * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / n
        preds = [intercept + slope * i for i in x]
        residuals = [float(v) - p for v, p in zip(y, preds)]
        std = (sum(r * r for r in residuals) / max(n - 2, 1)) ** 0.5
        mid_log = preds[-1]
        lower_log = mid_log - LINREG_STD_MULT * std
        upper_log = mid_log + LINREG_STD_MULT * std
        mid = math.exp(mid_log)
        lower = math.exp(lower_log)
        upper = math.exp(upper_log)
        p = safe_float(current_price)
        dist_lower = None
        pos = None
        if p is not None and lower > 0:
            dist_lower = ((p - lower) / lower) * 100
            if upper > lower:
                pos = clip(((p - lower) / (upper - lower)) * 100, 0, 100)
        out.update({
            "linreg_available": True,
            "linreg_mid_w": mid,
            "linreg_lower_w": lower,
            "linreg_upper_w": upper,
            "linreg_dist_lower_pct": dist_lower,
            "linreg_position_pct": pos,
        })
        return out
    except Exception as exc:
        out["linreg_error"] = str(exc)
        return out


def technical_metrics(item: dict[str, str]) -> dict[str, Any]:
    symbol = item["yahoo"]
    row = {
        "ticker": item["ticker"], "yahoo": symbol, "tv": item.get("tv", ""), "name": item.get("name", ""),
        "last_price": None, "previous_close": None, "daily_change_pct": None, "currency": "",
        "sma200w": None, "dist_pct": None, "hist_min_w_pct": None, "hist_min_w_date": None,
        "hist_min_w_low": None, "hist_min_equivalent": None, "hist_max_w_pct": None,
        "hist_max_w_date": None, "hist_max_w_high": None, "hist_max_equivalent": None,
        "gap_points": None, "below_sma200w": False, "orange_zone": False,
        "near_hist_min_w": False, "near_linreg_lower": False, "confluence_count": 0,
        "technical_label": "Monitor tecnico", "error": "",
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
        row["near_hist_min_w"] = bool(row["gap_points"] is not None and row["gap_points"] <= SMA200_HIST_MIN_PROXIMITY_POINTS)
        row["orange_zone"] = orange_zone(row["dist_pct"], row["hist_min_w_pct"])
        row.update(compute_linreg_w(close, row.get("last_price")))
        row["near_linreg_lower"] = bool(row.get("linreg_dist_lower_pct") is not None and abs(float(row.get("linreg_dist_lower_pct"))) <= LINREG_NEAR_LOWER_PCT)
        conditions = [bool(row["below_sma200w"]), bool(row["near_hist_min_w"]), bool(row["near_linreg_lower"])]
        row["confluence_count"] = sum(1 for v in conditions if v)
        if row["confluence_count"] == 3:
            row["technical_label"] = "Buy Zone tecnica"
        elif row["confluence_count"] == 2:
            row["technical_label"] = "Watch tecnico"
        else:
            row["technical_label"] = "Monitor tecnico"
        return row
    except Exception as exc:
        row["error"] = str(exc)
        return row


def build_record(item: dict[str, str]) -> dict[str, Any]:
    record = technical_metrics(item)
    record["tradingview_url"] = tv_chart_url(str(record.get("tv") or item.get("tv") or ""))
    return record


def sort_priority(record: dict[str, Any]) -> tuple[int, float, str]:
    cc = int(record.get("confluence_count") or 0)
    gap = safe_float(record.get("gap_points"))
    lin = safe_float(record.get("linreg_dist_lower_pct"))
    return (-cc, gap if gap is not None else 999, abs(lin) if lin is not None else 999, str(record.get("ticker") or ""))


def scan_symbols(limit: int | None = None, progress_callback: Callable[[int, int, dict[str, str]], None] | None = None) -> list[dict[str, Any]]:
    symbols = SYMBOLS[:limit] if limit else SYMBOLS
    records = []
    total = len(symbols)
    for idx, item in enumerate(symbols, 1):
        if progress_callback:
            progress_callback(idx, total, item)
        records.append(build_record(item))
        if idx < total and SLEEP_BETWEEN_TICKERS_SECONDS > 0:
            time.sleep(SLEEP_BETWEEN_TICKERS_SECONDS)
    return sorted(records, key=sort_priority)


def scan_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(records),
        "buy_count": len([r for r in records if int(r.get("confluence_count") or 0) == 3]),
        "watch_count": len([r for r in records if int(r.get("confluence_count") or 0) == 2]),
        "orange_count": len([r for r in records if bool(r.get("orange_zone"))]),
        "errors_count": len([r for r in records if str(r.get("error") or "").strip()]),
        "last_update": now_rome().strftime("%d/%m/%Y %H:%M:%S"),
    }
