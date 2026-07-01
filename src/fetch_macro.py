# -*- coding: utf-8 -*-
"""Fetch macroeconomic time series from Alpha Vantage.

Captures: CPI, NONFARM_PAYROLL, UNEMPLOYMENT, FEDERAL_FUNDS_RATE,
TREASURY_YIELD, RETAIL_SALES, INFLATION. Each saved to data/macro/.
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from dotenv import load_dotenv  # noqa: E402
import pandas as pd  # noqa: E402

load_dotenv(REPO / ".env")
AVKEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "")

MACRO = REPO / "data" / "macro"
MACRO.mkdir(parents=True, exist_ok=True)

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

SERIES = {
    "CPI": ("CPI 月度同比/指数", "monthly"),
    "NONFARM_PAYROLL": ("非农就业人口", "monthly"),
    "UNEMPLOYMENT": ("失业率%", "monthly"),
    "FEDERAL_FUNDS_RATE": ("有效联邦基金利率%", "monthly"),
    "TREASURY_YIELD": {"daily": "10年期国债收益率%"},  # special: needs interval
    "RETAIL_SALES": ("零售销售", "monthly"),
    "INFLATION": ("通胀率年度%", "annual"),
}


def fetch(func, interval=None):
    params = "function={}&apikey={}".format(func, AVKEY)
    if interval:
        params += "&interval={}".format(interval)
    url = "https://www.alphavantage.co/query?{}".format(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=30, context=_CTX)
    return json.loads(r.read())


def main():
    for func, spec in SERIES.items():
        try:
            if func == "TREASURY_YIELD":
                d = fetch(func, interval="daily")
            else:
                interval = spec[1] if isinstance(spec, tuple) else None
                d = fetch(func, interval=interval)
            data = d.get("data", [])
            if not data:
                print("[SKIP] {} no data: {}".format(func, d.get("Error Message", d.get("Note", ""))[:50]))
                continue
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.sort_values("date").reset_index(drop=True)
            df.to_parquet(MACRO / "{}.parquet".format(func), index=False)
            df.to_csv(MACRO / "{}.csv".format(func), index=False, encoding="utf-8-sig")
            name = spec[0] if isinstance(spec, tuple) else list(spec.values())[0]
            print("[OK] {} ({}, {}): {} rows, {} -> {}".format(
                func, name, df["date"].iloc[0].date(), len(df),
                str(df["date"].iloc[0].date()), str(df["date"].iloc[-1].date())))
        except Exception as e:
            print("[ERR] {}: {}".format(func, str(e)[:60]))
        time.sleep(1.5)


if __name__ == "__main__":
    main()
