# -*- coding: utf-8 -*-
"""Generic single-stock historical backtest analysis.

Computes a comprehensive metric set from daily adj_close and emits a Markdown
report. Used by analyze_tech_stock.py to generate per-ticker reports.

Metric set:
  - total return, CAGR, annualized vol, Sharpe, Sortino
  - max drawdown (peak-to-trough) + recovery time
  - win/loss day balance (yin-yang), best/worst day
  - monthly seasonality, best/worst month, rolling 12m stats
  - correlation with SPY/QQQ benchmark (where overlap exists)
  - leverage liquidation sensitivity (1x/2x/3x at worst MDD)
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"
PROC = REPO / "data" / "processed"


def load_daily(symbol):
    f = RAW / "daily_{}.parquet".format(symbol)
    df = pd.read_parquet(f)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    # Use adj_close (split+dividend adjusted total-return series) when it is
    # sane. Yahoo's backwards-adjustment occasionally produces negative or
    # non-positive values for some Korean listings (a known Yahoo bug), in
    # which case we fall back to raw close and flag it.
    adj = df["adj_close"]
    adj_sane = adj.notna() & (adj > 0)
    if adj_sane.all():
        df["px"] = adj.astype(float)
        df["price_basis"] = "adj_close (split+dividend adjusted)"
    else:
        df["px"] = df["close"].astype(float)
        df["price_basis"] = "close (raw; Yahoo adj_close had {} non-positive values, treated as unreliable)".format(int((~adj_sane).sum()))
    df["ret"] = df["px"].pct_change().fillna(0.0)
    return df


def trading_days_per_year(df):
    return len(df) / max((df["date"].iloc[-1] - df["date"].iloc[0]).days / 365.25, 1e-9)


def max_drawdown(px):
    s = pd.Series(px).reset_index(drop=True)
    peak = s.cummax()
    dd = s / peak - 1.0
    mdd = float(dd.min())
    trough_i = int(dd.idxmin())
    peak_i = int(s.iloc[: trough_i + 1].idxmax())
    # recovery: first date after the trough at which price returns to peak_val
    peak_val = float(s.iloc[peak_i])
    after = s.iloc[trough_i:]
    rec_mask = after >= peak_val
    rec_i = None
    if rec_mask.any():
        rec_rel = int(rec_mask.values.argmax())
        rec_i = trough_i + rec_rel
        # guard against the pathological case where the trough itself is the
        # only "recovery" (peak==trough, e.g. MDD is a single-day spike at end)
        if rec_i >= len(s):
            rec_i = None
    return {
        "mdd_pct": round(mdd * 100, 2),
        "peak_date": None,
        "trough_date": None,
        "peak_idx": peak_i,
        "trough_idx": trough_i,
        "recovery_idx": rec_i,
    }


def enrich_mdd_dates(df, m):
    m["peak_date"] = str(df["date"].iloc[m["peak_idx"]].date())
    m["trough_date"] = str(df["date"].iloc[m["trough_idx"]].date())
    if m["recovery_idx"] is not None:
        m["recovery_date"] = str(df["date"].iloc[m["recovery_idx"]].date())
        m["recovery_days"] = int((df["date"].iloc[m["recovery_idx"]] - df["date"].iloc[m["peak_idx"]]).days)
        m["recovered"] = True
    else:
        m["recovery_date"] = None
        m["recovery_days"] = None
        m["recovered"] = False
    return m


def win_loss_balance(returns):
    up = int((returns > 0).sum())
    down = int((returns < 0).sum())
    flat = int((returns == 0).sum())
    return {
        "up_days": up,
        "down_days": down,
        "flat_days": flat,
        "up_ratio_pct": round(up / max(len(returns), 1) * 100, 2),
        "best_day_pct": round(float(returns.max()) * 100, 2),
        "worst_day_pct": round(float(returns.min()) * 100, 2),
    }


def monthly_seasonality(df):
    d = df.set_index("date")["ret"].copy()
    monthly = d.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    monthly.index = monthly.index.to_period("M")
    by_month = {}
    table = []
    for m in range(1, 13):
        vals = monthly[monthly.index.month == m]
        if len(vals) == 0:
            continue
        avg = float(vals.mean()) * 100
        pos = int((vals > 0).sum())
        by_month[m] = {"avg_pct": round(avg, 2), "pos_years": pos, "total_years": len(vals)}
        table.append((m, round(avg, 2), pos, len(vals)))
    best_m = max(by_month.items(), key=lambda kv: kv[1]["avg_pct"])
    worst_m = min(by_month.items(), key=lambda kv: kv[1]["avg_pct"])
    return {
        "by_month": by_month,
        "best_month": {"month": best_m[0], **best_m[1]},
        "worst_month": {"month": worst_m[0], **worst_m[1]},
    }


def annual_returns(df):
    d = df.set_index("date")["ret"].copy()
    annual = d.resample("YE").apply(lambda x: (1 + x).prod() - 1)
    annual.index = annual.index.year
    return {int(y): round(float(v) * 100, 2) for y, v in annual.items()}


def rolling_window_stats(returns, window=252):
    s = pd.Series(returns)
    roll = s.rolling(window).apply(lambda x: (1 + x).prod() - 1, raw=True)
    roll = roll.dropna()
    if len(roll) == 0:
        return {}
    return {
        "window_days": window,
        "best_rolling_pct": round(float(roll.max()) * 100, 2),
        "worst_rolling_pct": round(float(roll.min()) * 100, 2),
        "pct_negative": round(float((roll < 0).mean()) * 100, 2),
    }


def correlation_with(df, bench_symbol):
    bf = RAW / "daily_{}.parquet".format(bench_symbol)
    if not bf.exists():
        return None
    b = pd.read_parquet(bf)
    b["date"] = pd.to_datetime(b["date"]).dt.tz_localize(None)
    b = b.sort_values("date").reset_index(drop=True)
    b["px"] = b["adj_close"].fillna(b["close"])
    b["bret"] = b["px"].pct_change()
    merged = pd.merge(df[["date", "ret"]], b[["date", "bret"]], on="date", how="inner")
    if len(merged) < 100:
        return None
    c = float(merged["ret"].corr(merged["bret"]))
    beta = float(
        np.cov(merged["ret"], merged["bret"], ddof=1)[0][1]
        / np.var(merged["bret"], ddof=1)
    )
    return {"symbol": bench_symbol, "corr": round(c, 3), "beta": round(beta, 3), "overlap_days": len(merged)}


def leverage_sensitivity(mdd_pct):
    """At the stock's worst historical MDD, what leverage survives?"""
    mdd = abs(mdd_pct) / 100.0
    if mdd == 0:
        return {}
    threshold = 1.0 / mdd  # leverage at which worst MDD = 100% loss
    rows = {}
    for lev in [1.0, 1.5, 2.0, 3.0, 5.0]:
        rows[lev] = {
            "loss_at_worst_mdd_pct": round(lev * mdd * 100, 1),
            "survives": lev * mdd < 1.0,
        }
    rows["critical_leverage"] = round(threshold, 2)
    return rows


def analyze(symbol, display_name, market, sector):
    df = load_daily(symbol)
    returns = df["ret"].values[1:]
    n_years = (df["date"].iloc[-1] - df["date"].iloc[0]).days / 365.25
    tdpy = trading_days_per_year(df)

    total_ret = float(df["px"].iloc[-1] / df["px"].iloc[0] - 1)
    cagr = float((df["px"].iloc[-1] / df["px"].iloc[0]) ** (1 / n_years) - 1) if n_years > 0 else 0
    ann_vol = float(np.std(returns, ddof=1) * np.sqrt(tdpy))
    rf = 0.02
    sharpe = float((cagr - rf) / ann_vol) if ann_vol > 0 else 0
    downside = returns[returns < 0]
    downside_vol = float(np.std(downside, ddof=1) * np.sqrt(tdpy)) if len(downside) > 1 else ann_vol
    sortino = float((cagr - rf) / downside_vol) if downside_vol > 0 else 0

    mdd = enrich_mdd_dates(df, max_drawdown(df["px"].values))
    wl = win_loss_balance(returns)
    season = monthly_seasonality(df)
    annual = annual_returns(df)
    rolling = rolling_window_stats(returns, 252)

    corr_spy = correlation_with(df, "SPY")
    corr_qqq = correlation_with(df, "QQQ")
    corr_ndq = correlation_with(df, "NASDAQ_COMPOSITE")

    lev = leverage_sensitivity(mdd["mdd_pct"])

    result = {
        "symbol": symbol,
        "display_name": display_name,
        "market": market,
        "sector": sector,
        "price_basis": str(df["price_basis"].iloc[0]),
        "data_source": "Yahoo Finance " + str(df["price_basis"].iloc[0]),
        "period_start": str(df["date"].iloc[0].date()),
        "period_end": str(df["date"].iloc[-1].date()),
        "trading_days": int(len(df)),
        "span_years": round(n_years, 2),
        "trading_days_per_year": round(tdpy, 1),
        "start_price": round(float(df["px"].iloc[0]), 4),
        "end_price": round(float(df["px"].iloc[-1]), 4),
        "total_return_pct": round(total_ret * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "annualized_vol_pct": round(ann_vol * 100, 2),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "max_drawdown": mdd,
        "win_loss": wl,
        "monthly_seasonality": season,
        "annual_returns": annual,
        "rolling_252d": rolling,
        "correlation": {"SPY": corr_spy, "QQQ": corr_qqq, "NASDAQ_COMPOSITE": corr_ndq},
        "leverage_sensitivity": lev,
    }
    return result


if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    r = analyze(sym, sym, "US", "Tech")
    print(json.dumps(r, indent=2, ensure_ascii=False, default=str))
