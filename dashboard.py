st_set_page_config(
    page_title="Sam AI Bot",
    page_icon="🤖",
    layout="wide"
)

col_logo, col_title = st.columns([1, 5])

with col_logo:
    st.image("logo.png", width=90)

with col_title:
    st.title("Sam AI Bot")
    st.caption("NIFTY — AI Analysis")
"""
NSE AI Dashboard (Streamlit)
Run:  streamlit run dashboard.py
Educational only - financial advice nahi hai.
"""
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import nse_ai_bot as bot

IST = ZoneInfo("Asia/Kolkata")
st.set_page_config(page_title="NSE AI Dashboard", page_icon="📈", layout="wide")

# ---------------- Sidebar ----------------
st.sidebar.title("⚙️ Settings")
preset = list(bot.INDEX_MAP.keys())
choice = st.sidebar.selectbox("Index / Stock", preset + ["Custom stock"])
if choice == "Custom stock":
    name = st.sidebar.text_input("NSE symbol (e.g. RELIANCE)", "RELIANCE").upper().strip()
    symbol, step = name + ".NS", None
else:
    name = choice
    symbol, step = bot.INDEX_MAP[choice]

interval = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "30m", "1h", "1d"], index=2)
live = st.sidebar.toggle("🔴 Live auto-refresh", value=True)
refresh_s = st.sidebar.slider("Refresh every (seconds)", 15, 300, 30, step=5)
candles = st.sidebar.slider("Candles on chart", 50, 300, 120, step=10)
show_pcr = st.sidebar.checkbox("Show PCR (NSE, indices only)", value=True)
st.sidebar.caption("Yahoo data thoda delayed ho sakta hai (~1-15 min). Order execution ke liye apne broker ka live feed use karein.")


# ---------------- Helpers ----------------
def market_status():
    now = datetime.now(IST)
    open_ = now.weekday() < 5 and dtime(9, 15) <= now.time() <= dtime(15, 30)
    return open_, now


@st.cache_data(ttl=15, show_spinner=False)
def load(symbol, interval):
    return bot.fetch(symbol, interval)


@st.cache_data(ttl=120, show_spinner=False)
def load_pcr(name):
    return bot.nse_pcr(name)


def make_chart(df, n):
    c = df["Close"]
    d = df.assign(
        EMA20=bot.ema(c, 20),
        EMA50=bot.ema(c, 50),
        BBU=bot.bollinger(c)[0],
        BBL=bot.bollinger(c)[2],
        RSI=bot.rsi(c),
    ).tail(n)
    fig = go.Figure()
    fig.add_candlestick(x=d.index, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"], name="Price")
    fig.add_scatter(x=d.index, y=d["EMA20"], name="EMA20", line=dict(width=1.5))
    fig.add_scatter(x=d.index, y=d["EMA50"], name="EMA50", line=dict(width=1.5))
    fig.add_scatter(x=d.index, y=d["BBU"], name="BB up", line=dict(width=0.8, dash="dot"), opacity=0.5)
    fig.add_scatter(x=d.index, y=d["BBL"], name="BB low", line=dict(width=0.8, dash="dot"), opacity=0.5)
    fig.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.05))
    rfig = go.Figure(go.Scatter(x=d.index, y=d["RSI"], name="RSI"))
    rfig.add_hline(y=70, line_dash="dot")
    rfig.add_hline(y=30, line_dash="dot")
    rfig.update_layout(height=160, margin=dict(l=0, r=0, t=10, b=0), yaxis_range=[0, 100])
    return fig, rfig


# ---------------- Live panel ----------------
def panel():
    open_, now = market_status()
    st.title(f"📈 {name} — AI Analysis")
    st.caption(
        f"{'🟢 Market OPEN' if open_ else '🔴 Market CLOSED (last available data)'}  |  "
        f"{now.strftime('%d-%b-%Y %H:%M:%S')} IST  |  {interval}"
    )

    try:
        df = load(symbol, interval)
        res = bot.analyze(df)
    except Exception as e:
        st.error(f"Data/analysis error: {e}")
        return

    prev = df["Close"].iloc[-2]
    chg = res["price"] - prev
    step_ = step or bot.guess_step(res["price"])
    _, strike_txt = bot.pick_strike(res["price"], step_, res["signal"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Price", f"{res['price']:.2f}", f"{chg:+.2f} ({chg / prev * 100:+.2f}%)")
    c2.metric("Direction", res["direction"].split(" ")[0], f"score {res['score']:+d}/6", delta_color="off")
    c3.metric("RSI / ADX", f"{res['rsi']:.0f} / {res['adx']:.0f}")
    c4.metric("ATR", f"{res['atr']:.2f}")

    sig = res["signal"]
    if sig.startswith("BUY CALL"):
        st.success(f"### 🟢 {sig}")
    elif sig.startswith("BUY PUT"):
        st.error(f"### 🔴 {sig}")
    else:
        st.warning(f"### ⏸️ {sig}")

    fig, rfig = make_chart(df, candles)
    st.plotly_chart(fig, use_container_width=True)
    st.plotly_chart(rfig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Why this signal?")
        for line in res["reasons"]:
            st.write("• " + line)
    with right:
        st.subheader("Levels & Trade plan")
        st.write(f"**Support:** {res['support']:.2f}   |   **Resistance:** {res['resistance']:.2f}")
        if "entry" in res:
            st.write(f"**Strike:** {strike_txt}")
            st.table(pd.DataFrame(
                {"Entry": [res["entry"]], "Stop-loss": [res["sl"]], "Target 1": [res["t1"]], "Target 2": [res["t2"]]}
            ).round(2))
            st.caption("Levels underlying price par hain, option premium par nahi.")
        else:
            st.info("Abhi koi trade setup nahi — wait karein.")
        if show_pcr and name in ("NIFTY", "BANKNIFTY", "FINNIFTY"):
            p = load_pcr(name)
            if p is not None:
                mood = "bullish" if p > 1.2 else "bearish" if p < 0.8 else "neutral"
                st.metric("PCR (OI)", f"{p:.2f}", mood, delta_color="off")
            else:
                st.caption("PCR abhi NSE se nahi mila (NSE kabhi block karta hai).")

    st.caption("⚠️ Educational only. Financial advice nahi. Options me poora premium doob sakta hai — SL zaroor lagayein.")


if live:
    st.fragment(run_every=refresh_s)(panel)()
else:
    panel()
    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()
