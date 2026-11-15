#!/usr/bin/env python3
"""
NSE AI Bot - Technical analysis + direction + CALL/PUT signal
Educational only. Financial advice nahi hai.
"""
import argparse
import time
import numpy as np
import pandas as pd

INDEX_MAP = {
    "NIFTY": ("^NSEI", 50),
    "BANKNIFTY": ("^NSEBANK", 100),
    "FINNIFTY": ("NIFTY_FIN_SERVICE.NS", 50),
    "SENSEX": ("^BSESN", 100),
}


# ---------------- Indicators ----------------
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def macd(close, fast=12, slow=26, sig=9):
    line = ema(close, fast) - ema(close, slow)
    signal = ema(line, sig)
    return line, signal, line - signal


def atr(df, n=14):
    pc = df["Close"].shift()
    tr = pd.concat(
        [df["High"] - df["Low"], (df["High"] - pc).abs(), (df["Low"] - pc).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def adx(df, n=14):
    up = df["High"].diff()
    dn = -df["Low"].diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n)
    pdi = 100 * pd.Series(plus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    mdi = 100 * pd.Series(minus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean(), pdi, mdi


def bollinger(close, n=20, k=2):
    m = close.rolling(n).mean()
    sd = close.rolling(n).std()
    return m + k * sd, m, m - k * sd


# ---------------- Analysis core ----------------
def analyze(df):
    df = df.dropna().copy()
    if len(df) < 60:
        raise ValueError("Kam data hai (kam se kam 60 candles chahiye)")

    c = df["Close"]
    e20, e50 = ema(c, 20), ema(c, 50)
    e200 = ema(c, 200) if len(df) >= 200 else None
    r = rsi(c)
    m_line, m_sig, m_hist = macd(c)
    a = atr(df)
    ad, pdi, mdi = adx(df)
    bu, bm, bl = bollinger(c)

    last = c.iloc[-1]
    score, reasons = 0, []

    def add(pts, text):
        nonlocal score
        score += pts
        reasons.append(f"{'+' if pts > 0 else ''}{pts}  {text}")

    if e20.iloc[-1] > e50.iloc[-1]:
        add(1, "EMA20 > EMA50 (short-term uptrend)")
    else:
        add(-1, "EMA20 < EMA50 (short-term downtrend)")
    if e200 is not None:
        if last > e200.iloc[-1]:
            add(1, "Price > EMA200 (long-term bullish)")
        else:
            add(-1, "Price < EMA200 (long-term bearish)")
    if last > e20.iloc[-1]:
        add(1, "Price EMA20 ke upar")
    else:
        add(-1, "Price EMA20 ke neeche")

    if m_hist.iloc[-1] > 0 and m_hist.iloc[-1] > m_hist.iloc[-2]:
        add(1, "MACD histogram positive & badh raha")
    elif m_hist.iloc[-1] < 0 and m_hist.iloc[-1] < m_hist.iloc[-2]:
        add(-1, "MACD histogram negative & gir raha")

    rv = r.iloc[-1]
    if rv > 70:
        add(-1, f"RSI {rv:.0f} overbought (pullback ka risk)")
    elif rv > 55:
        add(1, f"RSI {rv:.0f} bullish zone")
    elif rv < 30:
        add(1, f"RSI {rv:.0f} oversold (bounce possible)")
    elif rv < 45:
        add(-1, f"RSI {rv:.0f} bearish zone")

    adxv = ad.iloc[-1]
    if adxv > 20:
        if pdi.iloc[-1] > mdi.iloc[-1]:
            add(1, f"ADX {adxv:.0f} strong trend, +DI > -DI")
        else:
            add(-1, f"ADX {adxv:.0f} strong trend, -DI > +DI")
    else:
        reasons.append(f" 0  ADX {adxv:.0f} weak trend / sideways")

    sideways = adxv < 20

    if score >= 3:
        direction = "BULLISH (Upar)"
    elif score <= -3:
        direction = "BEARISH (Neeche)"
    else:
        direction = "SIDEWAYS / Unclear"

    if score >= 3 and not sideways:
        signal = "BUY CALL (CE)"
    elif score <= -3 and not sideways:
        signal = "BUY PUT (PE)"
    else:
        signal = "WAIT - clear signal nahi"

    atrv = a.iloc[-1]
    out = {
        "price": last,
        "direction": direction,
        "signal": signal,
        "score": score,
        "reasons": reasons,
        "rsi": rv,
        "adx": adxv,
        "atr": atrv,
        "ema20": e20.iloc[-1],
        "ema50": e50.iloc[-1],
        "support": df["Low"].tail(20).min(),
        "resistance": df["High"].tail(20).max(),
        "bb_upper": bu.iloc[-1],
        "bb_lower": bl.iloc[-1],
    }
    if signal.startswith("BUY CALL"):
        out["entry"], out["sl"], out["t1"], out["t2"] = last, last - 1.5 * atrv, last + 1.5 * atrv, last + 3 * atrv
    elif signal.startswith("BUY PUT"):
        out["entry"], out["sl"], out["t1"], out["t2"] = last, last + 1.5 * atrv, last - 1.5 * atrv, last - 3 * atrv
    return out


def pick_strike(price, step, signal):
    atm = round(price / step) * step
    if signal.startswith("BUY CALL"):
        return atm, f"{atm} CE (ATM)  |  aggressive: {atm + step} CE"
    if signal.startswith("BUY PUT"):
        return atm, f"{atm} PE (ATM)  |  aggressive: {atm - step} PE"
    return atm, "-"


def guess_step(price):
    for limit, step in [(250, 2.5), (500, 5), (1000, 10), (2500, 20), (5000, 50), (1e9, 100)]:
        if price < limit:
            return step


# ---------------- Data ----------------
def fetch(symbol, interval="15m"):
    import yfinance as yf

    period = {"1m": "5d", "5m": "30d", "15m": "60d", "30m": "60d", "1h": "180d", "1d": "2y"}.get(interval, "60d")
    df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def nse_pcr(symbol):
    try:
        import requests

        h = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=h, timeout=8)
        d = s.get(f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}", headers=h, timeout=8).json()
        rec = d["filtered"]
        return rec["PE"]["totOI"] / rec["CE"]["totOI"]
    except Exception:
        return None


# ---------------- Terminal report ----------------
def report(name, symbol, step, interval):
    df = fetch(symbol, interval)
    res = analyze(df)
    step = step or guess_step(res["price"])
    _, strike_txt = pick_strike(res["price"], step, res["signal"])

    print("=" * 56)
    print(f" {name}  |  {interval}  |  {time.strftime('%d-%b-%Y %H:%M')}")
    print("=" * 56)
    print(f" Price      : {res['price']:.2f}")
    print(f" Direction  : {res['direction']}   (score {res['score']:+d}/6)")
    print(f" SIGNAL     : {res['signal']}")
    print("-" * 56)
    for line in res["reasons"]:
        print("  " + line)
    print("-" * 56)
    print(f" Support    : {res['support']:.2f}    Resistance: {res['resistance']:.2f}")
    if "entry" in res:
        print(f" Strike     : {strike_txt}")
        print(f" Underlying : Entry {res['entry']:.2f} | SL {res['sl']:.2f} | T1 {res['t1']:.2f} | T2 {res['t2']:.2f}")
    print("=" * 56)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--interval", default="15m", choices=["1m", "5m", "15m", "30m", "1h", "1d"])
    ap.add_argument("--watch", type=int, default=0)
    a = ap.parse_args()
    while True:
        for s in a.symbols:
            u = s.upper()
            sym, step = INDEX_MAP.get(u, (u if u.startswith("^") or "." in u else u + ".NS", None))
            try:
                report(u, sym, step, a.interval)
            except Exception as e:
                print(f"{u}: error - {e}")
        if not a.watch:
            break
        time.sleep(a.watch * 60)


if __name__ == "__main__":
    main()
