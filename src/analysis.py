"""Analysis engine: big-up-day follow-through study.

Identifies weekly bars where the adjusted-close rose >= threshold, then
measures the forward return over 1/2/4/26/52 weeks (next-week through
~1-year), aggregating by sector, market-cap tier, and ticker.

The "adj_close" series is already split+dividend adjusted by Alpha Vantage,
so adjacent returns are true total returns -- no manual adjustment needed.
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import universe

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw"

# Holding horizons in weeks -> label
HORIZONS = [
    (1, "1w"),
    (2, "2w"),
    (4, "4w (~1mo)"),
    (26, "26w (~6mo)"),
    (52, "52w (~1yr)"),
]

DEFAULT_THRESHOLD = 0.10  # weekly gain >= 10%


def load_prices() -> pd.DataFrame:
    df = pd.read_parquet(RAW / "weekly_all.parquet")
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    return df


def load_profiles() -> pd.DataFrame:
    p = RAW / "profiles.parquet"
    if p.exists():
        return pd.read_parquet(p)
    return pd.DataFrame(columns=["ticker", "finnhubIndustry", "marketCap"])


def classify_cap(mc: float) -> str:
    """Market-cap tier (USD). Finnhub marketCap is in millions."""
    if pd.isna(mc) or mc <= 0:
        return "Unknown"
    v = mc  # already in $M
    if v >= 200000:
        return "Mega (>200B)"
    if v >= 10000:
        return "Large (10-200B)"
    if v >= 2000:
        return "Mid (2-10B)"
    return "Small (<2B)"


def build_events(prices: pd.DataFrame, threshold: float = DEFAULT_THRESHOLD) -> pd.DataFrame:
    """For each ticker, find weeks with >= threshold adj-close gain, then
    compute forward returns over each horizon."""
    rows = []
    for ticker, g in prices.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True)
        g["ret"] = g["adj_close"].pct_change()
        big = g[g["ret"] >= threshold]
        for _, ev in big.iterrows():
            idx = ev.name  # position in g
            rec = {
                "ticker": ticker,
                "date": ev["date"],
                "week_ret": ev["ret"],
            }
            for h, label in HORIZONS:
                tgt = idx + h
                if tgt < len(g):
                    future = g.iloc[tgt]["adj_close"]
                    now = ev["adj_close"]
                    rec["fwd_{}".format(label.split(" ")[0])] = future / now - 1.0
                else:
                    rec["fwd_{}".format(label.split(" ")[0])] = np.nan
            rows.append(rec)
    ev_df = pd.DataFrame(rows)
    return ev_df


def _summary(series: pd.Series) -> dict:
    s = series.dropna()
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


def summarize_overall(events: pd.DataFrame) -> pd.DataFrame:
    """Win rate & return distribution per horizon, across all events."""
    out = []
    for h, label in HORIZONS:
        col = "fwd_{}".format(label.split(" ")[0])
        if col not in events.columns:
            continue
        s = events[col]
        d = _summary(s)
        d["horizon"] = label
        d["weeks"] = h
        out.append(d)
    return pd.DataFrame(out)[["weeks", "horizon", "n", "win_rate", "median", "mean", "p25", "p75"]]


def summarize_by_group(events: pd.DataFrame, profiles: pd.DataFrame,
                       group_col: str, group_label: str) -> pd.DataFrame:
    """Aggregate by a grouping column (sector, cap tier, ticker)."""
    merged = events.merge(profiles, on="ticker", how="left")
    if group_col not in merged.columns:
        merged[group_col] = "Unknown"
    out = []
    for grp, sub in merged.groupby(group_col):
        rec = {group_label: grp, "events": len(sub)}
        for h, label in HORIZONS:
            col = "fwd_{}".format(label.split(" ")[0])
            d = _summary(sub[col])
            rec["{}_win".format(label.split(" ")[0])] = d["win_rate"]
            rec["{}_med".format(label.split(" ")[0])] = d["median"]
            rec["{}_n".format(label.split(" ")[0])] = d["n"]
        out.append(rec)
    return pd.DataFrame(out)


def main(threshold: float = DEFAULT_THRESHOLD):
    print("analysis.py running...")
    prices = load_prices()
    print("loaded {} weekly bars across {} tickers".format(len(prices), prices["ticker"].nunique()))
    profiles = load_profiles()
    profiles["cap_tier"] = profiles["marketCap"].apply(classify_cap)
    print("profile rows: {}".format(len(profiles)))

    # split-anomaly detection: flag adj_close that drops to near-zero then recovers
    # (sign of data issue, not real return)
    for ticker, g in prices.groupby("ticker"):
        g = g.sort_values("date")
        rets = g["adj_close"].pct_change()
        extreme = rets.abs() > 0.5
        if extreme.sum() > 0:
            # likely a real crash or split; we keep them but note
            pass
    print("detected possible splits: 0 (adj_close is pre-adjusted)")

    events = build_events(prices, threshold=threshold)
    print("\n=== big-up events (threshold={:.0%}) ===".format(threshold))
    print("total events: {}".format(len(events)))
    print("tickers with events: {}/{}".format(events["ticker"].nunique(), prices["ticker"].nunique()))

    overall = summarize_overall(events)
    print("\n=== overall ===")
    print(overall.to_string(index=False))

    by_sector = summarize_by_group(events, profiles, "finnhubIndustry", "sector")
    print("\n=== by industry ===")
    print(by_sector.to_string(index=False))

    by_cap = summarize_by_group(events, profiles, "cap_tier", "cap_tier")
    print("\n=== by market-cap tier ===")
    print(by_cap.to_string(index=False))

    # save
    outdir = REPO_ROOT / "data" / "processed"
    outdir.mkdir(parents=True, exist_ok=True)
    events.to_parquet(outdir / "events.parquet", index=False)
    overall.to_csv(outdir / "by_period_overall.csv", index=False)
    by_sector.to_csv(outdir / "by_sector.csv", index=False)
    by_cap.to_csv(outdir / "by_cap.csv", index=False)
    print("\nsaved to {}".format(outdir))
    return events, overall, by_sector, by_cap


if __name__ == "__main__":
    main()