"""
AI Pro engine: features -> ML probability -> walk-forward honesty test + global mood.
Educational only. Koi bhi model future ki guarantee nahi deta.
"""
import numpy as np
import pandas as pd
import nse_ai_bot as bot

GLOBAL = {
    "S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow": "^DJI", "Nikkei": "^N225", "Hang Seng": "^HSI",
    "FTSE": "^FTSE", "DAX": "^GDAXI", "India VIX": "^INDIAVIX", "USD/INR": "USDINR=X",
    "Crude": "CL=F", "Gold": "GC=F", "US 10Y": "^TNX", "Dollar Idx": "DX-Y.NYB",
}
G_FEATS = ["S&P 500", "Nasdaq", "USD/INR", "Crude", "India VIX", "Dollar Idx"]


def _flat(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _naive(idx):
    idx = pd.to_datetime(idx)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()


# ---------------- Data ----------------
def fetch(symbol, interval="1d"):
    import yfinance as yf
    period = {"1d": "8y", "1h": "2y", "30m": "60d", "15m": "60d", "5m": "60d"}.get(interval, "2y")
    return _flat(yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True))


def global_history(period="6y"):
    import yfinance as yf
    raw = yf.download(list(GLOBAL.values()), period=period, interval="1d", progress=False, auto_adjust=True)["Close"]
    raw = raw.rename(columns={v: k for k, v in GLOBAL.items()})
    raw.index = _naive(raw.index)
    return raw[~raw.index.duplicated()].sort_index().ffill()


# ---------------- Global mood ----------------
def global_snapshot(hist):
    rows = []
    for name in hist.columns:
        s = hist[name].dropna()
        if len(s) >= 2:
            rows.append({"Market": name, "Last": round(float(s.iloc[-1]), 2),
                         "Change %": round(float(s.iloc[-1] / s.iloc[-2] - 1) * 100, 2)})
    return pd.DataFrame(rows)


def global_mood(snap):
    """Simple heuristic score (model nahi): risk-on/risk-off for India."""
    ch = dict(zip(snap["Market"], snap["Change %"]))
    eq = [ch[k] for k in ("S&P 500", "Nasdaq", "Dow", "DAX", "FTSE", "Nikkei", "Hang Seng") if k in ch]
    score = (np.mean(eq) if eq else 0)
    score -= 0.05 * ch.get("India VIX", 0)
    score -= 0.10 * ch.get("Crude", 0)
    score -= 0.50 * ch.get("USD/INR", 0)
    score -= 0.30 * ch.get("Dollar Idx", 0)
    label = "POSITIVE (risk-on)" if score > 0.4 else "NEGATIVE (risk-off)" if score < -0.4 else "MIXED / NEUTRAL"
    return round(float(score), 2), label


# ---------------- Features ----------------
def build_features(df, glob=None):
    c, h, l, o = df["Close"], df["High"], df["Low"], df["Open"]
    X = pd.DataFrame(index=df.index)
    for n in (1, 3, 5, 10, 20):
        X[f"ret{n}"] = c.pct_change(n)
    e20, e50 = bot.ema(c, 20), bot.ema(c, 50)
    X["d_e20"] = c / e20 - 1
    X["e20_e50"] = e20 / e50 - 1
    X["rsi"] = bot.rsi(c) / 100
    X["macd"] = bot.macd(c)[2] / c
    X["atr"] = bot.atr(df) / c
    ad, pdi, mdi = bot.adx(df)
    X["adx"] = ad / 100
    X["di"] = (pdi - mdi) / 100
    bu, _, bl = bot.bollinger(c)
    X["pctb"] = (c - bl) / (bu - bl).replace(0, np.nan)
    X["range"] = (h - l) / c
    X["gap"] = o / c.shift() - 1
    X["vol20"] = c.pct_change().rolling(20).std()
    if "Volume" in df and df["Volume"].sum() > 0:
        X["vol_z"] = np.log((df["Volume"] + 1) / (df["Volume"].rolling(20).mean() + 1))
    if glob is not None:
        g = glob.pct_change()
        dates = _naive(X.index)
        for k in G_FEATS:
            if k in g:
                s = g[k].dropna()
                X["g_" + k] = s.reindex(dates, method="ffill").values
    return X.replace([np.inf, -np.inf], np.nan)


def make_xy(df, glob, h):
    X = build_features(df, glob)
    fwd = df["Close"].shift(-h) / df["Close"] - 1
    y = (fwd > 0).astype(int)
    return X, y, fwd


# ---------------- Model + honest test ----------------
def new_model():
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=120,
                                          l2_regularization=1.0, min_samples_leaf=40, random_state=0)


def walk_forward(df, glob=None, h=1, n_splits=5, thr=0.55, cost=0.0003):
    """Expanding-window out-of-sample test. Isme future ka data kabhi training me nahi jaata."""
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import TimeSeriesSplit
    X, y, fwd = make_xy(df, glob, h)
    ok = X.notna().all(axis=1) & fwd.notna()
    X, y, fwd = X[ok], y[ok], fwd[ok]
    if len(X) < 400:
        raise ValueError(f"Kam data ({len(X)} rows). Kam se kam 400 chahiye.")
    probs = pd.Series(np.nan, index=X.index)
    for tr, te in TimeSeriesSplit(n_splits=n_splits, gap=h).split(X):
        m = new_model().fit(X.iloc[tr], y.iloc[tr])
        probs.iloc[te] = m.predict_proba(X.iloc[te])[:, 1]
    p = probs.dropna()
    yo, fo = y.loc[p.index], fwd.loc[p.index]
    acc = float(((p > 0.5).astype(int) == yo).mean())
    base = float(max(yo.mean(), 1 - yo.mean()))
    auc = float(roc_auc_score(yo, p))
    idx = p.index[::h]  # non-overlapping trades
    pos = np.where(p.loc[idx] > thr, 1, np.where(p.loc[idx] < 1 - thr, -1, 0))
    net = pos * fo.loc[idx].values - cost * np.abs(pos)
    tr_mask = pos != 0
    trades = int(tr_mask.sum())
    avg = float(net[tr_mask].mean()) if trades else 0.0
    eq = np.cumsum(net)
    rep = {
        "samples": int(len(p)), "accuracy": acc, "baseline": base, "auc": auc,
        "trades": trades, "win_rate": float((net[tr_mask] > 0).mean()) if trades else 0.0,
        "avg_trade": avg, "total": float(net.sum()),
        "max_dd": float((eq - np.maximum.accumulate(eq)).min()) if len(eq) else 0.0,
        "buy_hold": float(fo.loc[idx].sum()),
        "equity": pd.Series(eq, index=idx),
    }
    rep["edge"] = bool(auc >= 0.54 and trades >= 30 and avg > 0)
    return rep


def predict_latest(df, glob=None, h=1):
    X, y, fwd = make_xy(df, glob, h)
    ok = X.notna().all(axis=1) & fwd.notna()
    m = new_model().fit(X[ok], y[ok])
    last = X.iloc[[-1]]
    if last.isna().any(axis=None):
        last = last.fillna(X[ok].median())
    return float(m.predict_proba(last)[:, 1][0])



def decide(p, rep, hi=0.58, lo=0.42):
    pct = int(round(p * 100))
    if not rep["edge"]:
        return "WAIT", "Test me edge pakka nahi nikla. Prediction par bharosa mat karo."
    if p >= hi:
        return "CALL bias", "Up-move ki probability " + str(pct) + "% hai."
    if p <= lo:
        return "PUT bias", "Up-move ki probability sirf " + str(pct) + "% hai."
    return "WAIT", "Probability " + str(pct) + "% hai, saaf signal nahi."
