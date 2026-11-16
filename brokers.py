"""Broker adapters: sirf READ-ONLY live price (LTP). Order code jaan-boojh kar nahi hai.
Keys code me mat likho. Streamlit app -> Settings -> Secrets me daalo:

[dhan]
client_id = "1100000000"
access_token = "eyJ..."      # Dhan ka token (kuch ghante/din me expire hota hai)

# Zerodha ke liye (optional):
# [zerodha]
# api_key = "xxxx"
# access_token = "yyyy"
"""
import requests
import streamlit as st


class DhanHQ:
    """Dhan v2 market-quote LTP. Keys 'NSE:RELIANCE', 'NSE:NIFTY 50', 'NSE:1333' (security id) ho sakti hain."""
    name = "Dhan"
    URL = "https://api.dhan.co/v2/marketfeed/ltp"
    MASTER = "https://images.dhan.co/api-data/api-scrip-master.csv"
    INDEX_IDS = {"NIFTY 50": 13, "NIFTY BANK": 25, "NIFTY FIN SERVICE": 27, "SENSEX": 51}
    COMMON = {"RELIANCE": 2885, "TCS": 11536, "HDFCBANK": 1333, "INFY": 1594, "ICICIBANK": 4963, "SBIN": 3045}
    _master = None

    def __init__(self, client_id, access_token):
        self.headers = {"access-token": str(access_token), "client-id": str(client_id),
                        "Content-Type": "application/json", "Accept": "application/json"}

    def _lookup(self, sym):
        if sym in self.COMMON:
            return self.COMMON[sym]
        try:
            if DhanHQ._master is None:
                import pandas as pd
                DhanHQ._master = pd.read_csv(self.MASTER, low_memory=False)
            m = DhanHQ._master
            row = m[(m["SEM_EXM_EXCH_ID"] == "NSE") & (m["SEM_SEGMENT"] == "E") & (m["SEM_TRADING_SYMBOL"] == sym)]
            return int(row.iloc[0]["SEM_SMST_SECURITY_ID"])
        except Exception:
            raise ValueError(f"'{sym}' ka Dhan security ID nahi mila. 'NSE:<security id>' likh kar try karo.")

    def _resolve(self, key):
        exch, _, sym = key.partition(":")
        sym = sym.strip().upper()
        if sym in self.INDEX_IDS:
            return "IDX_I", self.INDEX_IDS[sym]
        seg = "BSE_EQ" if exch.upper() == "BSE" else "NSE_EQ"
        return seg, int(sym) if sym.isdigit() else self._lookup(sym)

    def ltp(self, symbols):
        want, payload = {}, {}
        for key in symbols:
            seg, sid = self._resolve(key)
            want[(seg, str(sid))] = key
            payload.setdefault(seg, []).append(sid)
        r = requests.post(self.URL, json=payload, headers=self.headers, timeout=10)
        if r.status_code != 200:
            raise RuntimeError(f"Dhan error {r.status_code}: {r.text[:200]}")
        out = {}
        for seg, items in (r.json().get("data") or {}).items():
            for sid, v in items.items():
                key = want.get((seg, str(sid)))
                if key:
                    out[key] = v.get("last_price")
        return out

    @staticmethod
    def symbol_for(name):
        return ZerodhaKite.symbol_for(name)


class ZerodhaKite:
    name = "Zerodha Kite"

    def __init__(self, api_key, access_token):
        from kiteconnect import KiteConnect
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)

    def ltp(self, symbols):
        data = self.kite.ltp(symbols)
        return {k: v["last_price"] for k, v in data.items()}

    @staticmethod
    def symbol_for(name):
        idx = {"NIFTY": "NSE:NIFTY 50", "BANKNIFTY": "NSE:NIFTY BANK", "FINNIFTY": "NSE:NIFTY FIN SERVICE",
               "SENSEX": "BSE:SENSEX"}
        return idx.get(name, f"NSE:{name}")


BROKERS = {"dhan": DhanHQ, "zerodha": ZerodhaKite}


def get_broker():
    try:
        for key, cls in BROKERS.items():
            if key in st.secrets:
                return cls(**dict(st.secrets[key])), None
    except FileNotFoundError:
        return None, None
    except Exception as e:
        return None, str(e)
    return None, None
