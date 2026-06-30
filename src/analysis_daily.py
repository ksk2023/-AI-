"""Daily analysis engine: big-up DAY follow-through.

Identifies daily bars where adjusted close rose >= threshold, then measures
forward returns over 1/5/10/21/126/252 trading days (~ 1d/1w/2w/1mo/6mo/1yr).
This directly answers the user's core question: "after a >10% up day,
what is the probability the NEXT DAY continues up?"
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"
PROC = REPO / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

# Holding horizons in TRADING DAYS -> user-facing label
HORIZONS = [
    (1, "1d (next day)"),
    (5, "5d (~1 week)"),
    (10, "10d (~2 weeks)"),
    (21, "21d (~1 month)"),
    (126, "126d (~6 months)"),
    (252, "252d (~1 year)"),
]

DEFAULT_THRESHOLD = 0.10


def load_prices():
    df = pd.read_parquet(RAW / "daily_all.parquet")
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


def load_profiles():
    p = RAW / "profiles.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def classify_cap(mc):
    if pd.isna(mc) or mc <= 0:
        return "Unknown"
    if mc >= 200000:
        return "Mega (>200B)"
    if mc >= 10000:
        return "Large (10-200B)"
    if mc >= 2000:
        return "Mid (2-10B)"
    return "Small (<2B)"


def build_events(prices, threshold=DEFAULT_THRESHOLD, use_intraday_signal=False):
    """Find days with >= threshold gain, compute forward returns."""
    rows = []
    for ticker, g in prices.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True)
        g = g.reset_index(drop=True)
        # daily return: adj_close pct_change (already split+div adjusted)
        g["ret"] = g["adj_close"].pct_change()
        if use_intraday_signal:
            # alternative: open->close same day >= threshold (gap-agnostic)
            g["signal"] = g["adj_close"] / g["open"] - 1
        else:
            g["signal"] = g["ret"]  # close-to-close from prior day
        big = g[g["signal"] >= threshold].copy()
        for _, ev in big.iterrows():
            idx = ev.name
            rec = {
                "ticker": ticker,
                "date": ev["date"],
                "signal_ret": ev["signal"],
                "close": ev["adj_close"],
            }
            for h, label in HORIZONS:
                tgt = idx + h
                col = "fwd_" + label.split(" ")[0]
                if tgt < len(g):
                    rec[col] = g.iloc[tgt]["adj_close"] / ev["adj_close"] - 1.0
                else:
                    rec[col] = np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


def _summary(s):
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0, "win_rate": np.nan, "median": np.nan, "mean": np.nan, "p25": np.nan, "p75": np.nan}
    return {
        "n": int(len(s)),
        "win_rate": float((s > 0).mean()),
        "median": float(s.median()),
        "mean": float(s.mean()),
        "p25": float(s.quantile(0.25)),
        "p75": float(s.quantile(0.75)),
    }


def summarize_overall(events):
    out = []
    for h, label in HORIZONS:
        col = "fwd_" + label.split(" ")[0]
        if col not in events.columns:
            continue
        d = _summary(events[col])
        d["horizon"] = label
        d["trading_days"] = h
        out.append(d)
    return pd.DataFrame(out)[["trading_days", "horizon", "n", "win_rate", "median", "mean", "p25", "p75"]]


def summarize_by_group(events, profiles, group_col, group_label):
    merged = events.merge(profiles, on="ticker", how="left")
    if group_col not in merged.columns:
        merged[group_col] = "Unknown"
    out = []
    for grp, sub in merged.groupby(group_col):
        rec = {group_label: grp, "events": len(sub)}
        for h, label in HORIZONS:
            col = "fwd_" + label.split(" ")[0]
            d = _summary(sub[col])
            tag = label.split(" ")[0]
            rec["{}_win".format(tag)] = d["win_rate"]
            rec["{}_med".format(tag)] = d["median"]
            rec["{}_n".format(tag)] = d["n"]
        out.append(rec)
    return pd.DataFrame(out)


def main(threshold=DEFAULT_THRESHOLD):
    prices = load_prices()
    profiles = load_profiles()
    profiles["cap_tier"] = profiles["marketCap"].apply(classify_cap)
    print("daily bars: {} | tickers: {} | profile rows: {}".format(
        len(prices), prices["ticker"].nunique(), len(profiles)))

    events = build_events(prices, threshold=threshold)
    print("\n=== big-up DAY events (threshold={:.0%}) ===".format(threshold))
    print("total: {} | tickers: {}/{}".format(
        len(events), events["ticker"].nunique(), prices["ticker"].nunique()))

    overall = summarize_overall(events)
    print("\n=== overall ===")
    print(overall.to_string(index=False))

    by_sector = summarize_by_group(events, profiles, "finnhubIndustry", "sector")
    by_cap = summarize_by_group(events, profiles, "cap_tier", "cap_tier")

    events.to_parquet(PROC / "daily_events.parquet", index=False)
    overall.to_csv(PROC / "daily_by_period.csv", index=False)
    by_sector.to_csv(PROC / "daily_by_sector.csv", index=False)
    by_cap.to_csv(PROC / "daily_by_cap.csv", index=False)
    print("\nsaved to {}".format(PROC))
    return events, overall, by_sector, by_cap


if __name__ == "__main__":
    main()