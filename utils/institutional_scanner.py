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
    {"ticker": "ACWI", "yahoo": "ACWI", "tv": "NASDAQ:ACWI", "name": "iShares MSCI ACWI ETF"},
    {"ticker": "SPY", "yahoo": "SPY", "tv": "AMEX:SPY", "name": "SPDR S&P 500 ETF Trust"},
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


def get_info(symbol: str) -> dict[str, Any]:
    """Same spirit as the local script: try get_info, return {} only on hard failure."""
    try:
        info = yf.Ticker(symbol).get_info()
        return info if isinstance(info, dict) else {}
    except Exception:
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
        score += 15
        notes.append("area arancione")
    elif row.get("below_sma200w"):
        score += 8
        notes.append("sotto SMA200W")
    elif dist is not None and dist < 10:
        score += 4
        notes.append("vicino SMA200W")
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
        if fpe <= 25:
            notes.append("FwdPE ok/basso")
    if peg is not None:
        score += 4 if peg <= 1.2 else 2 if peg <= 2.0 else 0
        if peg <= 1.2:
            notes.append("PEG buono")
    if fcfy is not None:
        score += 5 if fcfy >= 5 else 3 if fcfy >= 3 else 1 if fcfy > 0 else 0
        if fcfy >= 3:
            notes.append("FCF yield ok")
    if ps is not None:
        score += 3 if ps <= 5 else 1 if ps <= 10 else 0
    if tgt is not None:
        score += 3 if tgt >= 15 else 1 if tgt >= 5 else 0
        if tgt >= 15:
            notes.append("upside target")
    return round(clip(score, 0, 20), 1), notes


def score_quality(f: dict[str, Any]) -> tuple[float, list[str]]:
    notes, score = [], 0.0
    roe, opm, pm, gm, dte, fcf = [safe_float(f.get(k)) for k in ["return_on_equity_pct", "operating_margin_pct", "profit_margin_pct", "gross_margin_pct", "debt_to_equity", "free_cashflow"]]
    if roe is not None:
        score += 5 if roe >= 25 else 3 if roe >= 15 else 0
        if roe >= 25:
            notes.append("ROE alto")
    if opm is not None:
        score += 5 if opm >= 25 else 3 if opm >= 15 else 0
        if opm >= 25:
            notes.append("margine operativo alto")
    if pm is not None:
        score += 4 if pm >= 20 else 2 if pm >= 10 else 0
    if gm is not None:
        score += 3 if gm >= 50 else 2 if gm >= 35 else 0
    if dte is not None:
        score += 2 if dte <= 80 else 1 if dte <= 150 else 0
    if fcf is not None and fcf > 0:
        score += 1
        notes.append("FCF positivo")
    return round(clip(score, 0, 20), 1), notes


def score_growth(f: dict[str, Any]) -> tuple[float, list[str]]:
    notes, score = [], 0.0
    rev, earn, rec, tgt = [safe_float(f.get(k)) for k in ["revenue_growth_pct", "earnings_growth_pct", "recommendation_mean", "target_upside_pct"]]
    if rev is not None:
        score += 5 if rev >= 15 else 3 if rev >= 5 else 1 if rev >= 0 else 0
        if rev >= 15:
            notes.append("ricavi in crescita")
    if earn is not None:
        score += 5 if earn >= 15 else 3 if earn >= 5 else 1 if earn >= 0 else 0
        if earn >= 15:
            notes.append("utili in crescita")
    if rec is not None:
        score += 3 if rec <= 2.0 else 2 if rec <= 2.7 else 0
        if rec <= 2.0:
            notes.append("analyst rating buono")
    if tgt is not None and tgt > 0:
        score += 2
    return round(clip(score, 0, 15), 1), notes


def score_risk_momentum(row: dict[str, Any], f: dict[str, Any]) -> tuple[float, list[str]]:
    notes, score = [], 0.0
    beta, mom26, mom52, dd52, vol = [safe_float(x) for x in [f.get("beta"), row.get("momentum_26w_pct"), row.get("momentum_52w_pct"), row.get("drawdown_52w_pct"), row.get("weekly_vol_52w_pct")]]
    if beta is not None:
        score += 4 if beta <= 1.0 else 3 if beta <= 1.3 else 1 if beta <= 1.7 else 0
        if beta <= 1.0:
            notes.append("beta difensivo")
    if mom26 is not None:
        score += 4 if mom26 > 10 else 3 if mom26 > 0 else 1 if mom26 > -10 else 0
        if mom26 > 10:
            notes.append("momentum 6m positivo")
    if mom52 is not None:
        score += 3 if mom52 > 10 else 2 if mom52 > 0 else 1 if mom52 > -15 else 0
    if dd52 is not None:
        score += 4 if dd52 > -10 else 2 if dd52 > -25 else 1 if dd52 > -40 else 0
    if vol is not None:
        score += 5 if vol <= 3 else 3 if vol <= 5 else 1 if vol <= 8 else 0
        if vol <= 3:
            notes.append("volatilità bassa")
    return round(clip(score, 0, 20), 1), notes


def institutional_label(score: float) -> str:
    if score >= STRONG_BUY_ZONE_THRESHOLD:
        return "Strong Buy Zone"
    if score >= BUY_ZONE_THRESHOLD:
        return "Buy Zone"
    if score >= 50:
        return "Watch"
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
    missing_groups: list[str] = []
    missing_fields: list[str] = []
    present_fields = 0
    total_fields = 0
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
    if ratio >= 0.80:
        label = "Dati completi"
    elif ratio > 0:
        label = "Dati parziali"
    else:
        label = "Fondamentali assenti"
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
        return {"status": "not_enough_data", "low": None, "high": None, "active": False}
    valid: list[float] = []
    for i in range(int((MAX_SIMULATED_DISCOUNT_PCT * 2) / SIMULATION_STEP_PCT) + 1):
        pct = -MAX_SIMULATED_DISCOUNT_PCT + i * SIMULATION_STEP_PCT
        price = current * (1 + pct / 100)
        if price <= 0:
            continue
        sim = simulate_at_price(record, price)
        if bool(sim.get("orange_zone")) and (safe_float(sim.get("score_total")) or 0) >= threshold:
            valid.append(price)
    if not valid:
        return {"status": "not_price_only", "low": None, "high": None, "active": False}
    active = bool(record.get("orange_zone")) and (safe_float(record.get("score_total")) or 0) >= threshold
    return {"status": "range", "low": min(valid), "high": max(valid), "active": active}


def format_zone_range(record: dict[str, Any], key: str) -> str:
    data = record.get(key)
    currency = str(record.get("currency") or "").upper()
    if not isinstance(data, dict):
        return "dati insufficienti"
    status = data.get("status")
    if status == "range":
        return ("attiva · " if data.get("active") else "") + fmt_price(data.get("low"), currency) + " - " + fmt_price(data.get("high"), currency)
    if status == "not_enough_data":
        return "dati insufficienti"
    return "non basta solo prezzo"


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
    record["tradingview_url"] = tv_chart_url(str(record.get("tv") or item.get("tv") or ""))
    record["buy_zone_range"] = find_zone_range(record, BUY_ZONE_THRESHOLD)
    record["strong_buy_zone_range"] = find_zone_range(record, STRONG_BUY_ZONE_THRESHOLD)
    record["buy_zone_text"] = format_zone_range(record, "buy_zone_range")
    record["strong_buy_zone_text"] = format_zone_range(record, "strong_buy_zone_range")
    return record


def sort_priority(record: dict[str, Any]) -> tuple[int, float, str]:
    score = safe_float(record.get("score_total")) or 0
    if score >= STRONG_BUY_ZONE_THRESHOLD:
        group = 0
    elif score >= BUY_ZONE_THRESHOLD:
        group = 1
    elif bool(record.get("orange_zone")):
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
    return {
        "count": len(records),
        "top_ticker": top.get("ticker", "-"),
        "top_score": top.get("score_total"),
        "buy_strong_count": len([r for r in records if (safe_float(r.get("score_total")) or 0) >= BUY_ZONE_THRESHOLD]),
        "orange_count": len([r for r in records if bool(r.get("orange_zone"))]),
        "partial_count": len([r for r in records if not r.get("data_complete", False)]),
        "errors_count": len([r for r in records if str(r.get("error") or "").strip()]),
        "last_update": now_rome().strftime("%d/%m/%Y %H:%M:%S"),
    }
