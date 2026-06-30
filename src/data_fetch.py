"""Data ingestion layer.

Fetches weekly-adjusted price history (Alpha Vantage) and company
profiles/industry classification (Finnhub) for the study universe,
caching to parquet so re-runs are cheap.

Free-tier constraints handled here:
  - Alpha Vantage: ~25 req/weekday. We sleep 13s between calls.
  - Finnhub: ~60 req/min. We sleep 1s between calls.
"""
from __future__ import annotations

import json
import ssl
import time
import urllib.request
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import universe

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def _get_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(url, timeout=timeout, context=_CTX) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_weekly_adjusted(symbol, api_key):
    """Return a DataFrame indexed by week with OHLCV + adjusted close."""
    url = (
        "https://www.alphavantage.co/query?"
        "function=TIME_SERIES_WEEKLY_ADJUSTED&symbol={}&apikey={}".format(symbol, api_key)
    )
    data = _get_json(url, timeout=30)
    # AV returns a key like "Weekly Adjusted Time Series"
    ts_key = next((k for k in data if "Time Series" in k), None)
    if ts_key is None:
        raise RuntimeError("AV returned no time series for {}: {}".format(symbol, str(data)[:200]))
    series = data[ts_key]
    rows = []
    for d, v in series.items():
        rows.append({
            "date": d,
            "open": float(v["1. open"]),
            "high": float(v["2. high"]),
            "low": float(v["3. low"]),
            "close": float(v["4. close"]),
            "adj_close": float(v["5. adjusted close"]),
            "volume": float(v["6. volume"]),
            "dividend": float(v["7. dividend amount"]),
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def fetch_all_weekly(force=False):
    """Download weekly history for every ticker in the universe."""
    cfg = config.CONFIG
    tickers = universe.all_tickers()
    frames = []
    for i, t in enumerate(tickers):
        out = RAW_DIR / "weekly_{}.parquet".format(t.replace("^", "x"))
        if out.exists() and not force:
            df = pd.read_parquet(out)
            print("[{}/{}] cached {}: {} weeks".format(i + 1, len(tickers), t, len(df)))
        else:
            ok = False
            for attempt in range(3):
                try:
                    df = fetch_weekly_adjusted(t, cfg.alpha_vantage_key)
                    df.insert(0, "ticker", t)
                    df.to_parquet(out, index=False)
                    print("[{}/{}] fetched {}: {} weeks ({} -> {})".format(
                        i + 1, len(tickers), t, len(df),
                        df["date"].min().date(), df["date"].max().date()))
                    ok = True
                    break
                except Exception as e:
                    print("  retry {} for {}: {}".format(attempt, t, e))
                    time.sleep(15)
            if not ok:
                print("  FAILED {}, skipping".format(t))
                continue
            time.sleep(13)
        frames.append(df)
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        all_df.to_parquet(RAW_DIR / "weekly_all.parquet", index=False)
        print("\nsaved combined ({} rows, {} tickers)".format(
            len(all_df), all_df["ticker"].nunique()))


def fetch_profiles():
    cfg = config.CONFIG
    tickers = universe.all_individual_tickers()
    rows = []
    for i, t in enumerate(tickers):
        try:
            p = _get_json(
                "https://finnhub.io/api/v1/stock/profile2?symbol={}&token={}".format(
                    t, cfg.finance_hub_key),
                timeout=20)
            rows.append({
                "ticker": t,
                "name": p.get("name"),
                "finnhubIndustry": p.get("finnhubIndustry"),
                "ggroup": p.get("ggroup"),
                "gsector": p.get("gsector"),
                "marketCap": p.get("marketCapitalization"),
                "exchange": p.get("exchange"),
                "ipo": p.get("ipo"),
                "country": p.get("country"),
            })
            print("[{}/{}] {}: {} cap={}".format(
                i + 1, len(tickers), t, p.get("finnhubIndustry"), p.get("marketCapitalization")))
        except Exception as e:
            print("  err {}: {}".format(t, e))
        time.sleep(1.1)
    df = pd.DataFrame(rows)
    out = RAW_DIR / "profiles.parquet"
    df.to_parquet(out, index=False)
    print("\nsaved profiles ({} rows)".format(len(df)))
    return df


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", action="store_true")
    ap.add_argument("--weekly", action="store_true")
    args = ap.parse_args()
    if not args.profiles and not args.weekly:
        args.profiles = True
        args.weekly = True
    if args.profiles:
        fetch_profiles()
    if args.weekly:
        fetch_all_weekly()