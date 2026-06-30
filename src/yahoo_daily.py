"""Yahoo Finance daily data fetcher using cookie+crumb auth.

Bypasses the 429 rate limit that affects the yfinance library by
performing the manual cookie -> crumb -> chart flow that Yahoo's
own web client uses.

NOTE: Yahoo is an unofficial data source. Prices are auto-adjusted
(split+dividend) by Yahoo's adjustedClose. We use raw close for
"big-up day" detection and note the survivorship caveat in the report.
"""
from __future__ import annotations

import http.cookiejar
import json
import ssl
import time
import urllib.request
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import universe

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")


class YahooFetcher:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj))
        self.opener.addheaders = [("User-Agent", _UA)]
        self.crumb = None

    def _init_auth(self):
        try:
            self.opener.open("https://fc.yahoo.com", timeout=15)
        except urllib.error.HTTPError:
            pass  # 404 is expected; cookie is set
        except Exception:
            pass
        try:
            resp = self.opener.open(
                "https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=15)
            self.crumb = resp.read().decode("utf-8").strip()
        except Exception as e:
            self.crumb = None
        return self.crumb is not None

    def fetch_daily(self, symbol, start="1999-01-01", end="2026-12-31"):
        if self.crumb is None:
            if not self._init_auth():
                raise RuntimeError("cannot get Yahoo crumb")
        p1 = int(time.mktime(time.strptime(start, "%Y-%m-%d")))
        p2 = int(time.mktime(time.strptime(end, "%Y-%m-%d")))
        # ^VIX etc need special handling; replace ^ for URL safety
        sym = symbol.replace("^", "%5E")
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/{}?"
               "period1={}&period2={}&interval=1d&crumb={}&includeAdjustedClose=true"
               .format(sym, p1, p2, self.crumb))
        for attempt in range(4):
            try:
                resp = self.opener.open(url, timeout=25)
                data = json.loads(resp.read())
                result = data["chart"]["result"][0]
                ts = result["timestamp"]
                quote = result["indicators"]["quote"][0]
                adj = result["indicators"].get("adjclose", [{}])[0]
                adj_close = adj.get("adjclose", [None] * len(ts))
                rows = []
                for i, t in enumerate(ts):
                    if quote["close"][i] is None:
                        continue
                    rows.append({
                        "date": pd.Timestamp(t, unit="s"),
                        "open": quote["open"][i],
                        "high": quote["high"][i],
                        "low": quote["low"][i],
                        "close": quote["close"][i],
                        "adj_close": adj_close[i] if adj_close[i] else quote["close"][i],
                        "volume": quote["volume"][i] if quote["volume"][i] else 0,
                    })
                df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
                return df
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(5 * (attempt + 1))
                    self._init_auth()
                    continue
                if e.code == 404:
                    return pd.DataFrame()
                time.sleep(3)
            except Exception as e:
                if attempt < 3:
                    time.sleep(3)
                    self._init_auth()
                else:
                    raise
        return pd.DataFrame()


def fetch_all_daily(force=False):
    yf = YahooFetcher()
    print("init Yahoo auth...", end=" ")
    ok = yf._init_auth()
    print("crumb OK" if ok else "FAILED")
    if not ok:
        return
    tickers = universe.all_tickers()
    frames = []
    for i, t in enumerate(tickers):
        out = RAW / "daily_{}.parquet".format(t.replace("^", "x"))
        if out.exists() and not force:
            df = pd.read_parquet(out)
        else:
            try:
                df = yf.fetch_daily(t)
                if len(df) == 0:
                    print("  [{}] {}: no data".format(i + 1, t))
                    continue
                df.insert(0, "ticker", t)
                df.to_parquet(out, index=False)
                time.sleep(0.5)
            except Exception as e:
                print("  [{}] {}: ERR {}".format(i + 1, t, str(e)[:60]))
                continue
        print("[{}/{}] {}: {} days ({} -> {})".format(
            i + 1, len(tickers), t, len(df),
            df["date"].min().date(), df["date"].max().date()))
        frames.append(df)
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        all_df.to_parquet(RAW / "daily_all.parquet", index=False)
        print("\nsaved daily_all.parquet ({} rows, {} tickers)".format(
            len(all_df), all_df["ticker"].nunique()))


if __name__ == "__main__":
    fetch_all_daily()