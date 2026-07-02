
from __future__ import annotations
import math, os, time, urllib.parse
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf
TIMEZONE=ZoneInfo("Europe/Rome")
SMA_WEEKS=200; SMA200_HIST_MIN_PROXIMITY_POINTS=10.0; SMA200_HIST_MIN_DIST_LIMIT=0.0
SLEEP_BETWEEN_TICKERS_SECONDS=float(os.getenv("INSTITUTIONAL_SCANNER_SLEEP","0.35"))
YF_REPAIR=os.getenv("YF_REPAIR","false").strip().lower() in {"1","true","yes","y"}
FIB_LEVELS=(0.500,0.618,0.786,0.887)
FIB_MAJOR_MIN_GAIN=float(os.getenv("INSTITUTIONAL_FIB_MAJOR_MIN_GAIN","0.80"))
FIB_MAJOR_MIN_WEEKS=int(os.getenv("INSTITUTIONAL_FIB_MAJOR_MIN_WEEKS","30"))
FIB_LOW_NEAR_SMA_PCT=float(os.getenv("INSTITUTIONAL_FIB_LOW_NEAR_SMA_PCT","0.03"))
SYMBOLS=[{'ticker': 'TSLA', 'yahoo': 'TSLA', 'tv': 'NASDAQ:TSLA', 'name': 'Tesla'}, {'ticker': 'COST', 'yahoo': 'COST', 'tv': 'NASDAQ:COST', 'name': 'Costco'}, {'ticker': 'MSFT', 'yahoo': 'MSFT', 'tv': 'NASDAQ:MSFT', 'name': 'Microsoft'}, {'ticker': 'V', 'yahoo': 'V', 'tv': 'NYSE:V', 'name': 'Visa'}, {'ticker': 'MA', 'yahoo': 'MA', 'tv': 'NYSE:MA', 'name': 'Mastercard'}, {'ticker': 'ORCL', 'yahoo': 'ORCL', 'tv': 'NYSE:ORCL', 'name': 'Oracle'}, {'ticker': 'PG', 'yahoo': 'PG', 'tv': 'NYSE:PG', 'name': 'Procter & Gamble'}, {'ticker': 'JNJ', 'yahoo': 'JNJ', 'tv': 'NYSE:JNJ', 'name': 'Johnson & Johnson'}, {'ticker': 'KO', 'yahoo': 'KO', 'tv': 'NYSE:KO', 'name': 'Coca-Cola'}, {'ticker': 'PEP', 'yahoo': 'PEP', 'tv': 'NASDAQ:PEP', 'name': 'PepsiCo'}, {'ticker': 'MCD', 'yahoo': 'MCD', 'tv': 'NYSE:MCD', 'name': "McDonald's"}, {'ticker': 'ABT', 'yahoo': 'ABT', 'tv': 'NYSE:ABT', 'name': 'Abbott Laboratories'}, {'ticker': 'WMT', 'yahoo': 'WMT', 'tv': 'NYSE:WMT', 'name': 'Walmart'}, {'ticker': 'AAPL', 'yahoo': 'AAPL', 'tv': 'NASDAQ:AAPL', 'name': 'Apple'}, {'ticker': 'GOOG', 'yahoo': 'GOOG', 'tv': 'NASDAQ:GOOG', 'name': 'Alphabet Class C'}, {'ticker': 'BRK.B', 'yahoo': 'BRK-B', 'tv': 'NYSE:BRK.B', 'name': 'Berkshire Hathaway'}, {'ticker': 'NVDA', 'yahoo': 'NVDA', 'tv': 'NASDAQ:NVDA', 'name': 'NVIDIA'}, {'ticker': 'ASML', 'yahoo': 'ASML', 'tv': 'NASDAQ:ASML', 'name': 'ASML Holding'}, {'ticker': 'META', 'yahoo': 'META', 'tv': 'NASDAQ:META', 'name': 'Meta Platforms'}, {'ticker': 'IBM', 'yahoo': 'IBM', 'tv': 'NYSE:IBM', 'name': 'IBM'}, {'ticker': 'AVGO', 'yahoo': 'AVGO', 'tv': 'NASDAQ:AVGO', 'name': 'Broadcom'}, {'ticker': 'AXP', 'yahoo': 'AXP', 'tv': 'NYSE:AXP', 'name': 'American Express'}, {'ticker': 'AMZN', 'yahoo': 'AMZN', 'tv': 'NASDAQ:AMZN', 'name': 'Amazon'}, {'ticker': 'CRM', 'yahoo': 'CRM', 'tv': 'NYSE:CRM', 'name': 'Salesforce'}]
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
    return txt+(f" {str(currency).upper()}" if currency else "")
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
    e=urllib.parse.quote(str(tv or "").strip(),safe="")
    return f"https://www.tradingview.com/chart/?symbol={e}" if e else ""
def hist_gap(dist,hist_min):
    d=safe_float(dist); h=safe_float(hist_min)
    return None if d is None or h is None else abs(d-h)
def below_sma(dist):
    d=safe_float(dist); return bool(d is not None and d<0)
def orange_zone(dist,hist_min):
    d=safe_float(dist)
    if d is None or d>=SMA200_HIST_MIN_DIST_LIMIT: return False
    g=hist_gap(d,hist_min); return bool(g is not None and g<=SMA200_HIST_MIN_PROXIMITY_POINTS)
def equivalent_price(sma,pct):
    s=safe_float(sma); p=safe_float(pct)
    return None if s is None or s<=0 or p is None else s*(1+p/100)
def fib_level_price(low,high,ratio): return high-(high-low)*ratio
def quote_data(symbol):
    last=prev=None; currency=""
    try:
        intr=normalize_df(yf_download(symbol,period="5d",interval="15m",auto_adjust=False))
        if not intr.empty and "Close" in intr.columns:
            intr=intr.dropna(subset=["Close"])
            if not intr.empty: last=safe_float(intr["Close"].iloc[-1])
    except Exception: pass
    try:
        daily=normalize_df(yf_download(symbol,period="10d",interval="1d",auto_adjust=False))
        if not daily.empty and "Close" in daily.columns:
            daily=daily.dropna(subset=["Close"])
            if last is None and not daily.empty: last=safe_float(daily["Close"].iloc[-1])
            if len(daily)>=2: prev=safe_float(daily["Close"].iloc[-2])
            elif len(daily)==1: prev=safe_float(daily["Close"].iloc[-1])
    except Exception: pass
    try:
        fast=yf.Ticker(symbol).fast_info; currency=str(fast.get("currency") or "").upper()
        if last is None: last=safe_float(fast.get("last_price") or fast.get("lastPrice"))
        if prev is None: prev=safe_float(fast.get("previous_close") or fast.get("previousClose"))
    except Exception: pass
    ch=None
    if last is not None and prev not in (None,0): ch=((last-prev)/prev)*100
    return {"last_price":last,"previous_close":prev,"daily_change_pct":ch,"currency":currency}
def compute_fibonacci_w(weekly,sma200_series,current_price):
    res={"fib_available":False,"fib_error":"","fib_low":None,"fib_low_date":None,"fib_high":None,"fib_high_date":None,"fib_0500":None,"fib_0618":None,"fib_0786":None,"fib_0887":None,"fib_first_buy_low":None,"fib_first_buy_high":None,"fib_buy_low":None,"fib_buy_high":None,"fib_strong_low":None,"fib_strong_high":None,"fib_marker_pct":None,"fib_status":"dati insufficienti","fib_swing_gain_pct":None,"fib_swing_weeks":None}
    try:
        if weekly is None or weekly.empty or "Low" not in weekly.columns or "High" not in weekly.columns: res["fib_error"]="weekly Low/High mancanti"; return res
        hist=weekly.copy(); hist["SMA200W"]=sma200_series
        hist=hist.dropna(subset=["Low","High","SMA200W"]); hist=hist[(hist["Low"]>0)&(hist["High"]>0)&(hist["SMA200W"]>0)]
        if hist.empty: res["fib_error"]="storico weekly insufficiente"; return res
        start=max(0,len(hist)-520); best=None
        for low_pos in range(start,len(hist)-FIB_MAJOR_MIN_WEEKS):
            low=safe_float(hist.iloc[low_pos]["Low"]); sma=safe_float(hist.iloc[low_pos]["SMA200W"])
            if low is None or sma is None or low>sma*(1+FIB_LOW_NEAR_SMA_PCT): continue
            after=hist.iloc[low_pos+FIB_MAJOR_MIN_WEEKS:]
            if after.empty: continue
            hi_idx=after["High"].astype(float).idxmax(); hi_pos=hist.index.get_loc(hi_idx); high=safe_float(hist.loc[hi_idx,"High"])
            if high is None or high<=low: continue
            gain=(high-low)/low; weeks=hi_pos-low_pos
            if gain<FIB_MAJOR_MIN_GAIN or weeks<FIB_MAJOR_MIN_WEEKS: continue
            recency=1/(1+max(0,(len(hist)-1-hi_pos))/260)
            score=gain*math.log1p(weeks)*(0.65+0.35*recency)
            if best is None or score>best[0]: best=(score,hist.index[low_pos],low,hi_idx,high,gain,weeks)
        if best is None: res["fib_error"]="nessuno swing primario significativo"; return res
        _,low_idx,low,hi_idx,high,gain,weeks=best
        lv={r:fib_level_price(low,high,r) for r in FIB_LEVELS}; f0500,f0618,f0786,f0887=lv[0.500],lv[0.618],lv[0.786],lv[0.887]
        p=safe_float(current_price); status="fuori area"; marker=None
        if p is not None:
            denom=f0500-f0887
            if denom>0: marker=clip(((f0500-p)/denom)*100,0,100)
            if f0618<=p<=f0500: status="Dentro Fib First Buy Area"
            elif f0786<=p<f0618: status="Dentro Fib Buy Area"
            elif f0887<=p<f0786: status="Dentro Fib Strong Buy Area"
            elif p>f0500: status=f"Fuori area - prezzo sopra 0.500 ({fmt_price(f0500)})"
            elif p<f0887: status=f"Sotto Fib Strong - prezzo sotto 0.887 ({fmt_price(f0887)})"
        def dt(idx): return idx.strftime("%Y-%m-%d") if hasattr(idx,"strftime") else str(idx)
        res.update({"fib_available":True,"fib_low":low,"fib_low_date":dt(low_idx),"fib_high":high,"fib_high_date":dt(hi_idx),"fib_0500":f0500,"fib_0618":f0618,"fib_0786":f0786,"fib_0887":f0887,"fib_first_buy_low":f0618,"fib_first_buy_high":f0500,"fib_buy_low":f0786,"fib_buy_high":f0618,"fib_strong_low":f0887,"fib_strong_high":f0786,"fib_marker_pct":marker,"fib_status":status,"fib_swing_gain_pct":gain*100,"fib_swing_weeks":weeks})
        return res
    except Exception as exc: res["fib_error"]=str(exc); return res
def technical_metrics(item):
    symbol=item["yahoo"]
    row={"ticker":item["ticker"],"yahoo":symbol,"tv":item.get("tv",""),"name":item.get("name",""),"last_price":None,"previous_close":None,"daily_change_pct":None,"currency":"","sma200w":None,"dist_pct":None,"hist_min_w_pct":None,"hist_min_w_date":None,"hist_min_w_low":None,"hist_min_equivalent":None,"hist_max_w_pct":None,"hist_max_w_date":None,"hist_max_w_high":None,"hist_max_equivalent":None,"gap_points":None,"below_sma200w":False,"orange_zone":False,"error":""}
    try:
        row.update(quote_data(symbol)); weekly=normalize_df(yf_download(symbol,period="20y",interval="1wk",auto_adjust=False))
        if weekly.empty or "Close" not in weekly.columns: row["error"]="weekly vuoto o Close mancante"; return row
        weekly=weekly.dropna(subset=["Close"])
        if len(weekly)<SMA_WEEKS: row["error"]=f"storico insufficiente: {len(weekly)} settimane"; return row
        close=weekly["Close"].astype(float); sma200_series=close.rolling(SMA_WEEKS).mean(); sma=safe_float(sma200_series.iloc[-1]); row["sma200w"]=sma
        if sma and row["last_price"] is not None: row["dist_pct"]=((row["last_price"]-sma)/sma)*100
        if "Low" in weekly.columns and "High" in weekly.columns:
            hist=weekly.copy(); hist["SMA200W"]=sma200_series; hist=hist.dropna(subset=["Low","High","SMA200W"]); hist=hist[(hist["Low"]>0)&(hist["High"]>0)&(hist["SMA200W"]>0)]
            below=hist[hist["Low"]<hist["SMA200W"]]
            if not below.empty:
                dd=((below["SMA200W"]-below["Low"])/below["SMA200W"])*100; mi=dd.idxmax(); row["hist_min_w_pct"]=-safe_float(dd.max()); row["hist_min_w_date"]=mi.strftime("%Y-%m-%d") if hasattr(mi,"strftime") else str(mi); row["hist_min_w_low"]=safe_float(below.loc[mi].get("Low")); row["hist_min_equivalent"]=equivalent_price(sma,row["hist_min_w_pct"])
            above=hist[hist["High"]>hist["SMA200W"]]
            if not above.empty:
                mx=((above["High"]-above["SMA200W"])/above["SMA200W"])*100; ma=mx.idxmax(); row["hist_max_w_pct"]=safe_float(mx.max()); row["hist_max_w_date"]=ma.strftime("%Y-%m-%d") if hasattr(ma,"strftime") else str(ma); row["hist_max_w_high"]=safe_float(above.loc[ma].get("High")); row["hist_max_equivalent"]=equivalent_price(sma,row["hist_max_w_pct"])
        row["gap_points"]=hist_gap(row["dist_pct"],row["hist_min_w_pct"]); row["below_sma200w"]=below_sma(row["dist_pct"]); row["orange_zone"]=orange_zone(row["dist_pct"],row["hist_min_w_pct"]); row.update(compute_fibonacci_w(weekly,sma200_series,row.get("last_price"))); return row
    except Exception as exc: row["error"]=str(exc); return row
def technical_label(r):
    if r.get("orange_zone") and r.get("fib_status")=="Dentro Fib Strong Buy Area": return "Area tecnica forte"
    if r.get("orange_zone"): return "Area arancione"
    if str(r.get("fib_status") or "").startswith("Dentro Fib"): return "Area Fibonacci"
    return "Monitor tecnico"
def build_record(item):
    r=technical_metrics(item); r["technical_label"]=technical_label(r); r["tradingview_url"]=tv_chart_url(str(r.get("tv") or item.get("tv") or "")); return r
def sort_priority(r):
    lab=str(r.get("technical_label") or ""); group=0 if lab=="Area tecnica forte" else 1 if lab=="Area arancione" else 2 if lab=="Area Fibonacci" else 3; g=safe_float(r.get("gap_points")); return (group,g if g is not None else 999,str(r.get("ticker") or ""))
def scan_symbols(limit=None, progress_callback: Callable[[int,int,dict],None]|None=None):
    syms=SYMBOLS[:limit] if limit else SYMBOLS; records=[]; total=len(syms)
    for i,item in enumerate(syms,1):
        if progress_callback: progress_callback(i,total,item)
        records.append(build_record(item))
        if i<total and SLEEP_BETWEEN_TICKERS_SECONDS>0: time.sleep(SLEEP_BETWEEN_TICKERS_SECONDS)
    return sorted(records,key=sort_priority)
def scan_summary(records):
    return {"count":len(records),"orange_count":len([r for r in records if bool(r.get("orange_zone"))]),"fib_count":len([r for r in records if str(r.get("fib_status") or "").startswith("Dentro Fib")]),"strong_fib_count":len([r for r in records if r.get("fib_status")=="Dentro Fib Strong Buy Area"]),"errors_count":len([r for r in records if str(r.get("error") or "").strip()]),"last_update":now_rome().strftime("%d/%m/%Y %H:%M:%S")}
