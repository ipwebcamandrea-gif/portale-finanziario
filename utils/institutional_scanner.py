from __future__ import annotations
import math, os, time, urllib.parse
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf
from utils.symbols import normalize_tradingview_symbol, normalize_yfinance_symbol, strip_exchange_prefix
from utils.advanced_buy_zones import analyze_advanced_buy_zone

TIMEZONE=ZoneInfo("Europe/Rome")
SMA_WEEKS=200

# V20: TradingView-like LinReg definition shown in the screenshot: "LinReg 100 close 2 2".
LINREG_LENGTH=int(os.getenv("INSTITUTIONAL_LINREG_LENGTH","100"))
LINREG_SOURCE=os.getenv("INSTITUTIONAL_LINREG_SOURCE","close").strip().lower()
LINREG_UPPER_MULT=float(os.getenv("INSTITUTIONAL_LINREG_UPPER_MULT","2.0"))
LINREG_LOWER_MULT=float(os.getenv("INSTITUTIONAL_LINREG_LOWER_MULT","2.0"))
LINREG_NEAR_LOWER_ABOVE_PCT=float(os.getenv("INSTITUTIONAL_LINREG_NEAR_LOWER_ABOVE_PCT","5.0"))
LINREG_NEAR_LOWER_BELOW_PCT=float(os.getenv("INSTITUTIONAL_LINREG_NEAR_LOWER_BELOW_PCT","10.0"))
SMA200_HIST_MIN_PROXIMITY_POINTS=float(os.getenv("INSTITUTIONAL_MIN_GAP_POINTS","10.0"))
SMA200_HIST_MIN_DIST_LIMIT=0.0
SLEEP_BETWEEN_TICKERS_SECONDS=float(os.getenv("INSTITUTIONAL_SCANNER_SLEEP","0.35"))
YF_REPAIR=os.getenv("YF_REPAIR","false").strip().lower() in {"1","true","yes","y"}
SYMBOLS=[{'ticker': 'TSLA', 'yahoo': 'TSLA', 'tv': 'NASDAQ:TSLA', 'name': 'Tesla'}, {'ticker': 'COST', 'yahoo': 'COST', 'tv': 'NASDAQ:COST', 'name': 'Costco'}, {'ticker': 'MSFT', 'yahoo': 'MSFT', 'tv': 'NASDAQ:MSFT', 'name': 'Microsoft'}, {'ticker': 'V', 'yahoo': 'V', 'tv': 'NYSE:V', 'name': 'Visa'}, {'ticker': 'MA', 'yahoo': 'MA', 'tv': 'NYSE:MA', 'name': 'Mastercard'}, {'ticker': 'ORCL', 'yahoo': 'ORCL', 'tv': 'NYSE:ORCL', 'name': 'Oracle'}, {'ticker': 'PG', 'yahoo': 'PG', 'tv': 'NYSE:PG', 'name': 'Procter & Gamble'}, {'ticker': 'JNJ', 'yahoo': 'JNJ', 'tv': 'NYSE:JNJ', 'name': 'Johnson & Johnson'}, {'ticker': 'KO', 'yahoo': 'KO', 'tv': 'NYSE:KO', 'name': 'Coca-Cola'}, {'ticker': 'PEP', 'yahoo': 'PEP', 'tv': 'NASDAQ:PEP', 'name': 'PepsiCo'}, {'ticker': 'MCD', 'yahoo': 'MCD', 'tv': 'NYSE:MCD', 'name': "McDonald's"}, {'ticker': 'ABT', 'yahoo': 'ABT', 'tv': 'NYSE:ABT', 'name': 'Abbott Laboratories'}, {'ticker': 'WMT', 'yahoo': 'WMT', 'tv': 'NYSE:WMT', 'name': 'Walmart'}, {'ticker': 'AAPL', 'yahoo': 'AAPL', 'tv': 'NASDAQ:AAPL', 'name': 'Apple'}, {'ticker': 'GOOG', 'yahoo': 'GOOG', 'tv': 'NASDAQ:GOOG', 'name': 'Alphabet Class C'}, {'ticker': 'BRK.B', 'yahoo': 'BRK-B', 'tv': 'NYSE:BRK.B', 'name': 'Berkshire Hathaway'}, {'ticker': 'NVDA', 'yahoo': 'NVDA', 'tv': 'NASDAQ:NVDA', 'name': 'NVIDIA'}, {'ticker': 'ASML', 'yahoo': 'ASML', 'tv': 'NASDAQ:ASML', 'name': 'ASML Holding'}, {'ticker': 'META', 'yahoo': 'META', 'tv': 'NASDAQ:META', 'name': 'Meta Platforms'}, {'ticker': 'IBM', 'yahoo': 'IBM', 'tv': 'NYSE:IBM', 'name': 'IBM'}, {'ticker': 'AVGO', 'yahoo': 'AVGO', 'tv': 'NASDAQ:AVGO', 'name': 'Broadcom'}, {'ticker': 'AXP', 'yahoo': 'AXP', 'tv': 'NYSE:AXP', 'name': 'American Express'}, {'ticker': 'AMZN', 'yahoo': 'AMZN', 'tv': 'NASDAQ:AMZN', 'name': 'Amazon'}, {'ticker': 'CRM', 'yahoo': 'CRM', 'tv': 'NYSE:CRM', 'name': 'Salesforce'}]

SYMBOL_NAME_OVERRIDES={
    "1MSFT.MI":"Microsoft su Milano",
    "1MSFT":"Microsoft su Milano",
    "MIL:1MSFT":"Microsoft su Milano",
    # Common watchlist symbols that may not be part of the default Mega Cap universe.
    "INTU":"Intuit",
    "NASDAQ:INTU":"Intuit",
    "NKE":"Nike",
    "NYSE:NKE":"Nike",
    "BABA":"Alibaba",
    "NYSE:BABA":"Alibaba",
}

def known_symbol_name(*values: str) -> str:
    """Return a friendly company name for watchlist symbols when available.

    Watchlists store plain symbols, not metadata. Without this lookup BUY ZONE
    FINDER cards can show only the ticker even though the legacy scanner universe
    already knows the company name.
    """
    keys=[]
    for value in values:
        raw=str(value or "").strip().upper()
        if not raw:
            continue
        keys.append(raw)
        if ":" in raw:
            keys.append(raw.split(":",1)[1])
        keys.append(raw.replace("-","."))
        keys.append(raw.replace(".","-"))
    for key in keys:
        if key in SYMBOL_NAME_OVERRIDES:
            return SYMBOL_NAME_OVERRIDES[key]
    for item in SYMBOLS:
        candidates={
            str(item.get("ticker") or "").strip().upper(),
            str(item.get("yahoo") or "").strip().upper(),
            str(item.get("tv") or "").strip().upper(),
        }
        candidates |= {c.split(":",1)[1] for c in list(candidates) if ":" in c}
        candidates |= {c.replace("-",".") for c in list(candidates)}
        candidates |= {c.replace(".","-") for c in list(candidates)}
        if any(key and key in candidates for key in keys):
            return str(item.get("name") or "").strip()
    return ""


COMPANY_NAME_CACHE: dict[str, str] = {}

def yfinance_company_name(yahoo_symbol: str) -> str:
    """Fetch a company name from yfinance only when no local name is available.

    This is a fallback for watchlists that contain only ticker strings not present
    in the built-in BUY ZONE FINDER universe. Results are cached in-process to
    avoid repeated get_info calls during the same Streamlit run.
    """
    symbol = str(yahoo_symbol or "").strip().upper()
    if not symbol:
        return ""
    if symbol in COMPANY_NAME_CACHE:
        return COMPANY_NAME_CACHE[symbol]

    name = ""
    try:
        ticker = yf.Ticker(symbol)
        info = {}
        try:
            info = ticker.get_info()
        except Exception:
            info = {}
        if not isinstance(info, dict) or not info:
            try:
                info = ticker.info
            except Exception:
                info = {}
        if isinstance(info, dict):
            name = str(
                info.get("longName")
                or info.get("shortName")
                or info.get("displayName")
                or info.get("quoteType")
                or ""
            ).strip()
    except Exception:
        name = ""

    # Avoid displaying the ticker again as if it were a company description.
    if name.upper() in {symbol, symbol.replace("-", "."), symbol.replace(".", "-")}:
        name = ""

    COMPANY_NAME_CACHE[symbol] = name
    return name

def now_rome(): return datetime.now(TIMEZONE)
def safe_float(v):
    try:
        if v is None: return None
        x=float(v)
        return None if pd.isna(x) or math.isinf(x) else x
    except Exception: return None
def clip(v,lo,hi): return max(lo,min(hi,v))
def fmt_price(v,currency=""):
    x=safe_float(v)
    if x is None: return "N/D"
    txt=f"{x:,.2f}".replace(",","_").replace(".",",").replace("_", ".")
    cur=str(currency or "").strip().upper()
    return txt+(f" {cur}" if cur else "")
def fmt_pct(v,digits=1):
    x=safe_float(v)
    return "N/D" if x is None else f"{x:+.{digits}f}%".replace(".",",")
def normalize_df(df):
    if df is None or df.empty: return pd.DataFrame()
    out=df.copy()
    if isinstance(out.columns,pd.MultiIndex):
        if "Close" in out.columns.get_level_values(0): out.columns=out.columns.get_level_values(0)
        elif "Close" in out.columns.get_level_values(-1): out.columns=out.columns.get_level_values(-1)
    return out
def yf_download(symbol,**kwargs):
    return yf.download(symbol, repair=True, progress=False, threads=False, **kwargs) if YF_REPAIR else yf.download(symbol, progress=False, threads=False, **kwargs)
def tv_chart_url(tv):
    e=urllib.parse.quote(str(tv or "").strip(), safe="")
    return f"https://www.tradingview.com/chart/?symbol={e}" if e else ""
def hist_gap(dist,hmin):
    d=safe_float(dist); h=safe_float(hmin)
    return None if d is None or h is None else abs(d-h)
def below_sma(dist):
    d=safe_float(dist); return bool(d is not None and d<0)
def orange_zone(dist,hmin):
    d=safe_float(dist)
    if d is None or d>=SMA200_HIST_MIN_DIST_LIMIT: return False
    g=hist_gap(d,hmin)
    return bool(g is not None and g<=SMA200_HIST_MIN_PROXIMITY_POINTS)
def equivalent_price(sma,pct):
    s=safe_float(sma); p=safe_float(pct)
    return None if s is None or s<=0 or p is None else s*(1+p/100)
def quote_data(symbol):
    last=prev=None; cur=""
    try:
        d=normalize_df(yf_download(symbol,period="10d",interval="1d",auto_adjust=False))
        if not d.empty and "Close" in d.columns:
            d=d.dropna(subset=["Close"])
            if not d.empty: last=safe_float(d["Close"].iloc[-1])
            if len(d)>=2: prev=safe_float(d["Close"].iloc[-2])
            elif len(d)==1: prev=last
    except Exception: pass
    try:
        f=yf.Ticker(symbol).fast_info
        cur=str(f.get("currency") or "").upper()
        if last is None: last=safe_float(f.get("last_price") or f.get("lastPrice"))
        if prev is None: prev=safe_float(f.get("previous_close") or f.get("previousClose"))
    except Exception: pass
    ch=((last-prev)/prev*100) if last is not None and prev not in (None,0) else None
    return {"last_price":last,"previous_close":prev,"daily_change_pct":ch,"currency":cur}
def _linreg(vals):
    n=len(vals)
    if n<2: return None
    x=list(range(n)); sx=sum(x); sy=sum(vals); sxx=sum(i*i for i in x); sxy=sum(i*v for i,v in zip(x,vals)); den=n*sxx-sx*sx
    if den==0: return None
    slope=(n*sxy-sx*sy)/den; intercept=(sy-slope*sx)/n; preds=[intercept+slope*i for i in x]
    residuals=[v-p for v,p in zip(vals,preds)]
    std=(sum(r*r for r in residuals)/max(n-2,1))**0.5
    return preds,std

def compute_linreg_w(weekly,current_price):
    out={"linreg_available":False,"linreg_error":"","linreg_mid_w":None,"linreg_lower_w":None,"linreg_upper_w":None,"linreg_dist_lower_pct":None,"linreg_position_pct":None,"linreg_anchor_high":None,"linreg_anchor_high_date":None,"linreg_weeks":None,"linreg_method":f"LinReg {LINREG_LENGTH} close {LINREG_UPPER_MULT:g} {LINREG_LOWER_MULT:g}"}
    try:
        if weekly is None or weekly.empty or "Close" not in weekly.columns:
            out["linreg_error"]="weekly Close mancante"; return out
        h=weekly.copy().dropna(subset=["Close"])
        h=h[h["Close"]>0]
        if len(h)<LINREG_LENGTH:
            out["linreg_error"]=f"storico linreg insufficiente: {len(h)} settimane"; return out
        win=h.iloc[-LINREG_LENGTH:].copy()
        vals=[float(v) for v in win["Close"].astype(float).tolist()]
        reg=_linreg(vals)
        if reg is None:
            out["linreg_error"]="regressione non valida"; return out
        preds,std=reg
        mid=preds[-1]
        lower=mid-LINREG_LOWER_MULT*std
        upper=mid+LINREG_UPPER_MULT*std
        if lower<=0: lower=min(vals)*0.80
        p=safe_float(current_price); dist=None; pos=None
        if p is not None and lower>0:
            dist=(p-lower)/lower*100
            if upper>lower: pos=clip((p-lower)/(upper-lower)*100,0,100)
        out.update({"linreg_available":True,"linreg_mid_w":mid,"linreg_lower_w":lower,"linreg_upper_w":upper,"linreg_dist_lower_pct":dist,"linreg_position_pct":pos,"linreg_weeks":LINREG_LENGTH})
        return out
    except Exception as e:
        out["linreg_error"]=str(e); return out

def technical_metrics(item):
    sym=item["yahoo"]
    row={"ticker":item["ticker"],"yahoo":sym,"tv":item.get("tv",""),"name":item.get("name",""),"last_price":None,"previous_close":None,"daily_change_pct":None,"currency":"","sma200w":None,"dist_pct":None,"hist_min_w_pct":None,"hist_min_w_date":None,"hist_min_w_low":None,"hist_min_equivalent":None,"hist_max_w_pct":None,"hist_max_w_date":None,"hist_max_w_high":None,"hist_max_equivalent":None,"gap_points":None,"below_sma200w":False,"orange_zone":False,"near_hist_min_w":False,"near_linreg_lower":False,"confluence_count":0,"technical_label":"Monitor tecnico","error":""}
    try:
        row.update(quote_data(sym)); w=normalize_df(yf_download(sym,period="20y",interval="1wk",auto_adjust=False))
        if w.empty or "Close" not in w.columns: row["error"]="weekly vuoto o Close mancante"; return row
        w=w.dropna(subset=["Close"])
        if len(w)<SMA_WEEKS: row["error"]=f"storico insufficiente: {len(w)} settimane"; return row
        close=w["Close"].astype(float); sma=close.rolling(SMA_WEEKS).mean(); s=safe_float(sma.iloc[-1]); row["sma200w"]=s
        if s and row["last_price"] is not None: row["dist_pct"]=(row["last_price"]-s)/s*100
        if "Low" in w.columns and "High" in w.columns:
            hist=w.copy(); hist["SMA200W"]=sma; hist=hist.dropna(subset=["Low","High","SMA200W"]); hist=hist[(hist["Low"]>0)&(hist["High"]>0)&(hist["SMA200W"]>0)]
            below=hist[hist["Low"]<hist["SMA200W"]]
            if not below.empty:
                dd=(below["SMA200W"]-below["Low"])/below["SMA200W"]*100; mi=dd.idxmax()
                row["hist_min_w_pct"]=-safe_float(dd.max()); row["hist_min_w_date"]=mi.strftime("%Y-%m-%d") if hasattr(mi,"strftime") else str(mi); row["hist_min_w_low"]=safe_float(below.loc[mi,"Low"]); row["hist_min_equivalent"]=equivalent_price(s,row["hist_min_w_pct"])
            above=hist[hist["High"]>hist["SMA200W"]]
            if not above.empty:
                mx=(above["High"]-above["SMA200W"])/above["SMA200W"]*100; ma=mx.idxmax()
                row["hist_max_w_pct"]=safe_float(mx.max()); row["hist_max_w_date"]=ma.strftime("%Y-%m-%d") if hasattr(ma,"strftime") else str(ma); row["hist_max_w_high"]=safe_float(above.loc[ma,"High"]); row["hist_max_equivalent"]=equivalent_price(s,row["hist_max_w_pct"])
        row["gap_points"]=hist_gap(row["dist_pct"],row["hist_min_w_pct"]); row["below_sma200w"]=below_sma(row["dist_pct"]); row["near_hist_min_w"]=bool(row["gap_points"] is not None and row["gap_points"]<=SMA200_HIST_MIN_PROXIMITY_POINTS); row["orange_zone"]=orange_zone(row["dist_pct"],row["hist_min_w_pct"])
        row.update(compute_linreg_w(w,row.get("last_price")))
        dl=safe_float(row.get("linreg_dist_lower_pct")); row["near_linreg_lower"]=bool(dl is not None and dl<=LINREG_NEAR_LOWER_ABOVE_PCT)
        # Buy Zone Avanzate: integrazione additiva e isolata.
        # Non modifica le tre condizioni tecniche esistenti; aggiunge solo campi
        # usati dalla card per la quarta riga V/X e per la sezione sotto LinReg.
        try:
            row.update(analyze_advanced_buy_zone(
                sym,
                current_price=row.get("last_price"),
                currency=row.get("currency") or "",
                weekly=w,
                linreg_lower=row.get("linreg_lower_w"),
                sma200w=row.get("sma200w"),
            ))
        except Exception as advanced_exc:
            row.update({
                "advanced_buyzone_available": False,
                "advanced_buyzone_error": str(advanced_exc),
                "advanced_signal_active": False,
                "advanced_signal_label": "Buy Zone Avanzate N/D",
                "advanced_signal_reason": "Dati avanzati non disponibili.",
            })
        # BUY ZONE FINDER now has 4 motivations:
        # 1) below SMA200W, 2) near historical Min W, 3) near/below LinReg Lower,
        # 4) real-options Advanced Buy Zone signal.
        c=[
            bool(row["below_sma200w"]),
            bool(row["near_hist_min_w"]),
            bool(row["near_linreg_lower"]),
            bool(row.get("advanced_signal_active")),
        ]
        row["confluence_count"]=sum(1 for v in c if v)
        row["technical_label"]=(
            "Buy Zone tecnica" if row["confluence_count"]==4 else
            "Watch tecnico" if row["confluence_count"]==3 else
            "Early tecnico" if row["confluence_count"]==2 else
            "Monitor tecnico"
        )
        return row
    except Exception as e: row["error"]=str(e); return row

def scanner_item_from_symbol(symbol: str) -> dict:
    """Build a scanner item from a Watchlist TradingView/yfinance symbol using central normalizers."""
    raw = str(symbol or "").strip().upper()
    if not raw:
        return {"ticker": "", "yahoo": "", "tv": "", "name": ""}
    yahoo = normalize_yfinance_symbol(raw)
    tv = normalize_tradingview_symbol(raw)
    tv_ticker = strip_exchange_prefix(tv).strip().upper() if tv else ""
    ticker = tv_ticker or str(yahoo or raw).replace("-", ".")
    name = known_symbol_name(raw, yahoo, tv, ticker)
    if not name:
        name = yfinance_company_name(yahoo)
    return {"ticker": ticker, "yahoo": yahoo, "tv": tv, "name": name}

def scanner_items_from_symbols(symbols) -> list[dict]:
    """Normalize watchlist symbols/dicts into scanner item dictionaries."""
    items=[]; seen=set()
    for entry in symbols or []:
        if isinstance(entry, dict):
            raw = str(entry.get("yahoo") or entry.get("ticker") or entry.get("tv") or "").strip().upper()
            item = scanner_item_from_symbol(raw)
            if entry.get("name"):
                item["name"] = str(entry.get("name") or "")
        else:
            item = scanner_item_from_symbol(str(entry))
        key = str(item.get("yahoo") or item.get("ticker") or "").strip().upper()
        if not key or key in seen:
            continue
        seen.add(key); items.append(item)
    return items

def build_record(item):
    r=technical_metrics(item); r["tradingview_url"]=tv_chart_url(str(r.get("tv") or item.get("tv") or "")); return r
def sort_priority(r):
    cc=int(r.get("confluence_count") or 0); gap=safe_float(r.get("gap_points")); lin=safe_float(r.get("linreg_dist_lower_pct")); return (-cc,gap if gap is not None else 999,abs(lin) if lin is not None else 999,str(r.get("ticker") or ""))
def scan_symbols(symbols=None, limit=None, progress_callback:Callable[[int,int,dict],None]|None=None):
    """Scan explicit watchlist symbols or the legacy hardcoded universe."""
    if symbols is None:
        arr = SYMBOLS[:limit] if limit else SYMBOLS
    else:
        arr = scanner_items_from_symbols(symbols)
        if limit:
            arr = arr[:limit]
    out=[]; total=len(arr)
    for i,it in enumerate(arr,1):
        if progress_callback: progress_callback(i,total,it)
        out.append(build_record(it))
        if i<total and SLEEP_BETWEEN_TICKERS_SECONDS>0: time.sleep(SLEEP_BETWEEN_TICKERS_SECONDS)
    return sorted(out,key=sort_priority)
def scan_summary(records):
    return {"count":len(records),"buy_count":len([r for r in records if int(r.get("confluence_count") or 0)==4]),"watch_count":len([r for r in records if int(r.get("confluence_count") or 0)==3]),"orange_count":len([r for r in records if bool(r.get("orange_zone"))]),"errors_count":len([r for r in records if str(r.get("error") or "").strip()]),"last_update":now_rome().strftime("%d/%m/%Y %H:%M:%S")}
