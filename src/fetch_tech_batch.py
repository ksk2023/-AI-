# -*- coding: utf-8 -*-
"""Fetch full daily history for the tech-stock research batch.

Targets (Yahoo symbols):
  美股七姐妹:   AAPL MSFT NVDA GOOGL META AMZN TSLA  (mostly already present)
  美光:        MU
  闪迪(历史):   SNDK   (Western Digital acquired 2016; delisted)
  闪迪(新):     SND    (re-spun off from WD in Feb 2025)
  康宁:        GLW
  迈威尔:      MRVL
  台积电ADR:    TSM
  台积电本股:   2330.TW
  海力士:      000660.KS
  三星:        005930.KS
  诺基亚:      NOK
  SpaceX:      SPCX (IPO 2026-06-12 on Nasdaq; short history)

Uses the existing cookie+crumb YahooFetcher (src/yahoo_daily.py).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402
from yahoo_daily import YahooFetcher  # noqa: E402

RAW = REPO / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# (yahoo_symbol, display_name_cn, market)
TARGETS = [
    ("AAPL",     "苹果",          "US"),
    ("MSFT",     "微软",          "US"),
    ("NVDA",     "英伟达",        "US"),
    ("GOOGL",    "谷歌-A",        "US"),
    ("META",     "Meta",          "US"),
    ("AMZN",     "亚马逊",        "US"),
    ("TSLA",     "特斯拉",        "US"),
    ("MU",       "美光",          "US"),
    ("SNDK",     "闪迪-旧(WD收购前1995-2016)", "US"),
    ("SND",      "闪迪-新(2025重新分拆)",      "US"),
    ("GLW",      "康宁",          "US"),
    ("MRVL",     "迈威尔",        "US"),
    ("TSM",      "台积电ADR",     "US"),
    ("2330.TW",  "台积电-台湾本股", "TW"),
    ("000660.KS","SK海力士",      "KR"),
    ("005930.KS","三星电子",      "KR"),
    ("NOK",      "诺基亚",        "US"),
]


def safe_name(symbol):
    return symbol.replace("^", "x").replace(".", "_")


def fetch_one(yf, symbol, display, market):
    out = RAW / "daily_{}.parquet".format(safe_name(symbol))
    if out.exists():
        df = pd.read_parquet(out)
        print("  [skip] {} ({}): {} days, {} -> {}".format(
            symbol, display, len(df), df["date"].min().date(), df["date"].max().date()))
        return True
    try:
        df = yf.fetch_daily(symbol)
        if len(df) == 0:
            print("  [FAIL] {} ({}): no data returned".format(symbol, display))
            return False
        df.insert(0, "ticker", symbol)
        df.to_parquet(out, index=False)
        print("  [OK] {} ({}): {} days, {} -> {}".format(
            symbol, display, len(df), df["date"].min().date(), df["date"].max().date()))
        return True
    except Exception as e:
        print("  [ERR] {} ({}): {}".format(symbol, display, str(e)[:80]))
        return False


def main():
    yf = YahooFetcher()
    print("init Yahoo auth...", end=" ")
    ok = yf._init_auth()
    print("crumb OK" if ok else "FAILED")
    if not ok:
        return
    ok_count = 0
    for sym, name, mkt in TARGETS:
        print("fetch {} [{}]...".format(sym, name))
        if fetch_one(yf, sym, name, mkt):
            ok_count += 1
        time.sleep(0.6)
    print("\n{} / {} tickers succeeded".format(ok_count, len(TARGETS)))


if __name__ == "__main__":
    main()
