"""AI Pro: global mood + ML probability + honest backtest + broker live price."""
import pandas as pd
import streamlit as st

import engine as eng
import nse_ai_bot as bot
import brokers

st.set_page_config(page_title="AI Pro", page_icon="🤖", layout="wide")
st.title("🤖 AI Pro: Global + India analysis")
st.caption("Educational only. Koi model sahi prediction ki guarantee nahi deta. Pehle paper trading karein.")

INDIA = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN"}
choices = list(INDIA) + list(eng.GLOBAL) + ["Indian stock (NSE)", "Custom Yahoo symbol"]
pick = st.sidebar.selectbox("Instrument", choices)
if pick in INDIA:
    name, symbol = pick, INDIA[pick]
elif pick in eng.GLOBAL:
    name, symbol = pick, eng.GLOBAL[pick]
elif pick == "Indian stock (NSE)":
    name = st.sidebar.text_input("NSE symbol", "RELIANCE").upper().strip()
    symbol = name + ".NS"
else:
    name = symbol = st.sidebar.text_input("Yahoo symbol", "AAPL").strip()

interval = st.sidebar.selectbox("Timeframe", ["1d", "1h", "15m"], index=0)
h = st.sidebar.slider("Kitne candle aage ka prediction", 1, 10, 1 if interval == "1d" else 4)
indian = symbol.startswith(("^NSE", "^BSE")) or symbol.endswith(".NS")
use_global = interval == "1d" and indian
st.sidebar.caption("1d + Indian instrument par global market ka data bhi model ko milta hai." if use_global
                   else "Global features sirf 1d + Indian instrument par lagte hain.")


@st.cache_data(ttl=900, show_spinner=False)
def load_global():
    return eng.global_history("6y")


@st.cache_data(ttl=300, show_spinner=False)
def load_px(symbol, interval):
    return eng.fetch(symbol, interval)


t_glob, t_ai, t_test, t_brk = st.tabs(["🌍 Global mood", "🤖 AI prediction", "🧪 Test (sachchai)", "🔌 Broker"])

with t_glob:
    try:
        gh = load_global()
        snap = eng.global_snapshot(gh)
        score, label = eng.global_mood(snap)
        c1, c2 = st.columns(2)
        c1.metric("Global mood (India ke liye)", label)
        c2.metric("Score", score)
        st.dataframe(snap, hide_index=True, use_container_width=True)
        st.caption("Mood ek simple rule hai (US/Europe/Asia up, VIX/crude/dollar/rupee down = positive), ML model nahi.")
    except Exception as e:
        gh = None
        st.error(f"Global data nahi mila: {e}")

with t_ai:
    if st.button("▶️ Model chalao (30-60 second)", type="primary"):
        try:
            with st.spinner("Data le raha hoon aur model train kar raha hoon..."):
                df = load_px(symbol, interval).dropna()
                glob = load_global() if use_global else None
                rep = eng.walk_forward(df, glob, h)
                p = eng.predict_latest(df, glob, h)
                tech = bot.analyze(df)
            st.session_state["ai"] = dict(name=name, rep=rep, p=p, tech=tech, h=h, interval=interval)
        except Exception as e:
            st.error(f"Error: {e}")
    s = st.session_state.get("ai")
    if s:
        rep, p, tech = s["rep"], s["p"], s["tech"]
        sig, why = eng.decide(p, rep)
        st.subheader(f"{s['name']}: {sig}")
        (st.success if sig == "CALL bias" else st.error if sig == "PUT bias" else st.warning)(why)
        a, b, c = st.columns(3)
        a.metric(f"Up-move probability ({s['h']} candle)", f"{p:.0%}")
        b.metric("Technical signal", tech["signal"].split(" (")[0].split(" -")[0])
        c.metric("Model test", "PASS ✅" if rep["edge"] else "FAIL ❌")
        tsig = tech["signal"]
        if rep["edge"] and ((sig == "CALL bias" and "CALL" in tsig) or (sig == "PUT bias" and "PUT" in tsig)):
            st.success("Model aur technical dono ek taraf hain. Ye sabse achhi taqat ka signal hota hai, phir bhi guarantee nahi.")
        elif sig != "WAIT" and ("WAIT" not in tsig):
            st.warning("Model aur technical alag taraf hain. Entry avoid karo.")
        if "entry" in tech:
            st.write(f"Technical levels: SL {tech['sl']:.2f} | T1 {tech['t1']:.2f} | T2 {tech['t2']:.2f}")
    else:
        st.info("Upar button dabao. Model sirf pichhle data par seekhta hai aur apna test khud karta hai.")

with t_test:
    s = st.session_state.get("ai")
    if not s:
        st.info("Pehle 'AI prediction' tab me model chalao.")
    else:
        rep = s["rep"]
        st.write("Ye test **walk-forward** hai: model sirf purane data par seekhta hai aur agle hisse par test hota hai. "
                 "Future ka data training me kabhi nahi jaata.")
        m1, m2, m3 = st.columns(3)
        m1.metric("Accuracy", f"{rep['accuracy']:.1%}", f"baseline {rep['baseline']:.1%}", delta_color="off")
        m2.metric("AUC (0.5 = sikka uchhalna)", f"{rep['auc']:.3f}")
        m3.metric("Test samples", rep["samples"])
        n1, n2, n3 = st.columns(3)
        n1.metric("Trades", rep["trades"])
        n2.metric("Win rate", f"{rep['win_rate']:.1%}")
        n3.metric("Avg trade (cost ke baad)", f"{rep['avg_trade']:.3%}")
        o1, o2 = st.columns(2)
        o1.metric("Total return (sum)", f"{rep['total']:.1%}", f"buy&hold {rep['buy_hold']:.1%}", delta_color="off")
        o2.metric("Max drawdown", f"{rep['max_dd']:.1%}")
        st.line_chart(rep["equity"])
        st.caption("PASS ka matlab: AUC >= 0.54, kam se kam 30 trades aur cost ke baad positive average. "
                   "Ye bhi bhavishya ki guarantee nahi, sirf itna batata hai ki purane data par kuch pakad me aaya.")

with t_brk:
    broker, err = brokers.get_broker()
    if err:
        st.error(f"Broker connect nahi hua: {err}")
    elif broker is None:
        st.info("Abhi koi broker jura nahi hai. Jab chaho, Streamlit app ke **Settings → Secrets** me key daalo. "
                "Format `brokers.py` ke upar likha hai.")
    else:
        st.success(f"{broker.name} connected (sirf price padhne ke liye).")
        syms = st.text_input("Symbols (comma)", "NIFTY,BANKNIFTY,RELIANCE")
        if st.button("Live price lo"):
            try:
                keys = [brokers.ZerodhaKite.symbol_for(x.strip().upper()) for x in syms.split(",") if x.strip()]
                st.dataframe(pd.DataFrame(broker.ltp(keys).items(), columns=["Symbol", "LTP"]),
                             hide_index=True, use_container_width=True)
            except Exception as e:
                st.error(f"Price nahi mila: {e}")
    st.caption("Is app me order lagane ka koi code nahi hai. Auto-trading se pehle apne broker ke API terms aur "
               "SEBI ke retail algo niyam check karna zaruri hai.")
