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
SMA200_HIST_MIN_PROXIMITY_POINTS = 10.0
SMA200_HIST_MIN_DIST_LIMIT = 0.0
SLEEP_BETWEEN_TICKERS_SECONDS = float(os.getenv("INSTITUTIONAL_SCANNER_SLEEP", "0.35"))
YF_REPAIR = os.getenv("YF_REPAIR", "false").strip().lower() in {"1", "true", "yes", "y"}
FIB_LEVELS = (0.500, 0.618, 0.786, 0.887)

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


def fib_level_price(low: float, high: float, ratio: float) -> float:
    return high - (high - low) * ratio


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


def compute_fibonacci_w(weekly: pd.DataFrame, sma200_series: pd.Series, current_price: Any) -> dict[str, Any]:
    result = {
        "fib_available": False, "fib_error": "", "fib_low": None, "fib_low_date": None,
        "fib_high": None, "fib_high_date": None, "fib_0500": None, "fib_0618": None,
        "fib_0786": None, "fib_0887": None, "fib_first_buy_low": None,
        "fib_first_buy_high": None, "fib_buy_low": None, "fib_buy_high": None,
        "fib_strong_low": None, "fib_strong_high": None, "fib_marker_pct": None,
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
        below_mask = (hist["Low"] < hist["SMA200W"]).tolist()
        if not any(below_mask):
            result["fib_error"] = "nessun ciclo sotto SMA200W"
            return result
        blocks = []
        pos = 0
        while pos < len(below_mask):
            if not below_mask[pos]:
                pos += 1
                continue
            start = pos
            while pos + 1 < len(below_mask) and below_mask[pos + 1]:
                pos += 1
            blocks.append((start, pos))
            pos += 1
        last_hist_pos = len(hist) - 1
        chosen = None
        for block_index in range(len(blocks) - 1, -1, -1):
            start_pos, end_pos = blocks[block_index]
            next_start_pos = blocks[block_index + 1][0] if block_index + 1 < len(blocks) else None
            if next_start_pos is None and (last_hist_pos - end_pos) < 12:
                continue
            cycle = hist.iloc[start_pos:end_pos + 1]
            low_idx = cycle["Low"].astype(float).idxmin()
            low_value = safe_float(cycle.loc[low_idx, "Low"])
            if low_value is None or low_value <= 0:
                continue
            low_pos = hist.index.get_loc(low_idx)
            high_search_end = (next_start_pos - 1) if next_start_pos is not None else last_hist_pos
            if high_search_end <= low_pos:
                continue
            after_low = hist.iloc[low_pos:high_search_end + 1]
            high_idx = after_low["High"].astype(float).idxmax()
            high_value = safe_float(after_low.loc[high_idx, "High"])
            if high_value is None or high_value <= low_value:
                continue
            if ((high_value - low_value) / low_value) < 0.25 or (high_search_end - end_pos) < 12:
                continue
            chosen = (low_idx, low_value, high_idx, high_value)
            break
        if not chosen:
            result["fib_error"] = "nessun ciclo completato significativo"
            return result
        low_idx, low_value, high_idx, high_value = chosen
        levels = {ratio: fib_level_price(low_value, high_value, ratio) for ratio in FIB_LEVELS}
        fib_0500, fib_0618, fib_0786, fib_0887 = levels[0.500], levels[0.618], levels[0.786], levels[0.887]
        p = safe_float(current_price)
        status = "fuori area"
        marker_pct = None
        if p is not None:
            denom = fib_0500 - fib_0887
            if denom > 0:
                marker_pct = clip(((fib_0500 - p) / denom) * 100, 0, 100)
            if fib_0618 <= p <= fib_0500:
                status = "Dentro Fib First Buy Area"
            elif fib_0786 <= p < fib_0618:
                status = "Dentro Fib Buy Area"
            elif fib_0887 <= p < fib_0786:
                status = "Dentro Fib Strong Buy Area"
            elif p > fib_0500:
                status = f"Fuori area · prezzo sopra 0.500 ({fmt_price(fib_0500)})"
            elif p < fib_0887:
                status = f"Sotto Fib Strong · prezzo sotto 0.887 ({fmt_price(fib_0887)})"
        def date_text(idx):
            return idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        result.update({
            "fib_available": True, "fib_low": low_value, "fib_low_date": date_text(low_idx),
            "fib_high": high_value, "fib_high_date": date_text(high_idx),
            "fib_0500": fib_0500, "fib_0618": fib_0618, "fib_0786": fib_0786, "fib_0887": fib_0887,
            "fib_first_buy_low": fib_0618, "fib_first_buy_high": fib_0500,
            "fib_buy_low": fib_0786, "fib_buy_high": fib_0618,
            "fib_strong_low": fib_0887, "fib_strong_high": fib_0786,
            "fib_marker_pct": marker_pct, "fib_status": status,
        })
        return result
    except Exception as exc:
        result["fib_error"] = str(exc)
        return result


def technical_metrics(item: dict[str, str]) -> dict[str, Any]:
    symbol = item["yahoo"]
    row = {
        "ticker": item["ticker"], "yahoo": symbol, "tv": item.get("tv", ""), "name": item.get("name", ""),
        "last_price": None, "previous_close": None, "daily_change_pct": None, "currency": "",
        "sma200w": None, "dist_pct": None, "hist_min_w_pct": None, "hist_min_w_date": None,
        "hist_min_w_low": None, "hist_min_equivalent": None, "hist_max_w_pct": None,
        "hist_max_w_date": None, "hist_max_w_high": None, "hist_max_equivalent": None,
        "gap_points": None, "below_sma200w": False, "orange_zone": False, "error": "",
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
        row["orange_zone"] = orange_zone(row["dist_pct"], row["hist_min_w_pct"])
        row.update(compute_fibonacci_w(weekly, sma200_series, row.get("last_price")))
        return row
    except Exception as exc:
        row["error"] = str(exc)
        return row


def technical_label(record: dict[str, Any]) -> str:
    if record.get("orange_zone") and record.get("fib_status") == "Dentro Fib Strong Buy Area":
        return "Area tecnica forte"
    if record.get("orange_zone"):
        return "Area arancione"
    if str(record.get("fib_status") or "").startswith("Dentro Fib"):
        return "Area Fibonacci"
    return "Monitor tecnico"


def build_record(item: dict[str, str]) -> dict[str, Any]:
    record = technical_metrics(item)
    record["technical_label"] = technical_label(record)
    record["tradingview_url"] = tv_chart_url(str(record.get("tv") or item.get("tv") or ""))
    return record


def sort_priority(record: dict[str, Any]) -> tuple[int, float, str]:
    label = str(record.get("technical_label") or "")
    if label == "Area tecnica forte": group = 0
    elif label == "Area arancione": group = 1
    elif label == "Area Fibonacci": group = 2
    else: group = 3
    gap = safe_float(record.get("gap_points"))
    return (group, gap if gap is not None else 999, str(record.get("ticker") or ""))


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
        "orange_count": len([r for r in records if bool(r.get("orange_zone"))]),
        "fib_count": len([r for r in records if str(r.get("fib_status") or "").startswith("Dentro Fib")]),
        "strong_fib_count": len([r for r in records if r.get("fib_status") == "Dentro Fib Strong Buy Area"]),
        "errors_count": len([r for r in records if str(r.get("error") or "").strip()]),
        "last_update": now_rome().strftime("%d/%m/%Y %H:%M:%S"),
    }
