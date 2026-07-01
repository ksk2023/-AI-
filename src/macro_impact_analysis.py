# -*- coding: utf-8 -*-
"""Macro factor impact analysis on US equities.

Quantifies how macro indicators (Fed rate, CPI inflation, unemployment,
nonfarm payrolls, treasury yields) affect SPY/QQQ/sector ETFs:
  1. correlation of macro changes with monthly returns (concurrent)
  2. lagged correlation = impulse response (impact duration)
  3. rolling regression R^2 = explanatory power over time
  4. regime-conditional: how sectors react under rising-rate vs falling-rate

All numbers from real data. No estimates.
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
MACRO = REPO / "data" / "macro"
PROC = REPO / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

SECTORS = [
    ("SPY", "标普500"), ("QQQ", "纳斯达克100"), ("DIA", "道琼斯"), ("IWM", "罗素2000"),
    ("XLK", "科技"), ("XLV", "医疗"), ("XLF", "金融"), ("XLE", "能源"),
    ("XLY", "可选消费"), ("XLP", "必需消费"), ("XLI", "工业"), ("XLU", "公用事业"), ("XLB", "材料"),
]

MACRO_FACTORS = {
    "FFR": ("FEDERAL_FUNDS_RATE", "联邦基金利率%"),
    "CPI_YOY": ("CPI", "CPI同比通胀%"),        # need to compute yoy
    "UNEMP": ("UNEMPLOYMENT", "失业率%"),
    "NFP_YOY": ("NONFARM_PAYROLL", "非农同比%"),
    "TNX": ("TREASURY_YIELD", "10年期国债%"),
}


def _to_month_end(series):
    """Reindex a monthly series onto a clean month-end grid with ffill."""
    # snap each date to its month-end, then reindex onto a full ME grid
    s = series.copy()
    s.index = s.index + pd.offsets.MonthEnd(0)
    s = s[~s.index.duplicated(keep="last")]
    grid = pd.date_range(s.index.min(), s.index.max(), freq="ME")
    return s.reindex(grid).ffill()


def load_macro_monthly():
    """Build a monthly macro dataframe on a unified month-end grid."""
    frames = {}
    # FFR
    ffr = pd.read_parquet(MACRO / "FEDERAL_FUNDS_RATE.parquet")
    ffr = ffr.set_index(pd.to_datetime(ffr["date"]))["value"]
    ffr = _to_month_end(ffr)
    frames["FFR_level"] = ffr
    frames["FFR_change"] = ffr.diff()

    # CPI yoy (index-based)
    cpi = pd.read_parquet(MACRO / "CPI.parquet")
    cpi = cpi.set_index(pd.to_datetime(cpi["date"]))["value"]
    cpi = _to_month_end(cpi)
    cpi_yoy = (cpi / cpi.shift(12) - 1) * 100
    frames["CPI_YOY_level"] = cpi_yoy
    frames["CPI_YOY_change"] = cpi_yoy.diff()

    # Unemployment
    un = pd.read_parquet(MACRO / "UNEMPLOYMENT.parquet")
    un = un.set_index(pd.to_datetime(un["date"]))["value"]
    un = _to_month_end(un)
    frames["UNEMP_level"] = un
    frames["UNEMP_change"] = un.diff()

    # Nonfarm yoy
    nfp = pd.read_parquet(MACRO / "NONFARM_PAYROLL.parquet")
    nfp = nfp.set_index(pd.to_datetime(nfp["date"]))["value"]
    nfp = _to_month_end(nfp)
    nfp_yoy = (nfp / nfp.shift(12) - 1) * 100
    frames["NFP_YOY_level"] = nfp_yoy
    frames["NFP_YOY_change"] = nfp_yoy.diff()

    # TNX monthly avg
    tnx = pd.read_parquet(MACRO / "TREASURY_YIELD.parquet")
    tnx = tnx.set_index(pd.to_datetime(tnx["date"]))["value"]
    tnx_me = tnx.resample("ME").mean()
    tnx_me.index = tnx_me.index + pd.offsets.MonthEnd(0)
    frames["TNX_level"] = tnx_me
    frames["TNX_change"] = tnx_me.diff()

    df = pd.DataFrame(frames)
    df = df.loc["1999-12-31":].copy()
    return df


def load_sector_monthly_returns():
    out = {}
    for sym, name in SECTORS:
        f = RAW / "daily_{}.parquet".format(sym)
        df = pd.read_parquet(f)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        df["px"] = df["adj_close"].fillna(df["close"])
        m = df.set_index("date")["px"].resample("ME").last().pct_change()
        m.name = sym
        out[sym] = m
    rets = pd.DataFrame(out)
    return rets


def concurrent_corr(macro_df, rets_df):
    """Correlation between macro factor changes and same-month returns."""
    aligned = macro_df.join(rets_df, how="inner").dropna(subset=["FFR_change"])
    rows = []
    factors = ["FFR_change", "CPI_YOY_change", "UNEMP_change", "NFP_YOY_change", "TNX_change"]
    for fac in factors:
        row = {"factor": fac}
        for sym, _ in SECTORS:
            if sym in aligned.columns:
                sub = aligned[[fac, sym]].dropna()
                if len(sub) >= 24:
                    row[sym] = round(float(sub[fac].corr(sub[sym])), 3)
        rows.append(row)
    return pd.DataFrame(rows)


def lagged_corr(macro_df, rets_df, max_lag=12):
    """Impulse response: correlation of macro change at t with return at t+k.

    Returns a DataFrame: factor, lag(months), SPY corr, QQQ corr.
    This reveals impact DURATION.
    """
    factors = ["FFR_change", "CPI_YOY_change", "UNEMP_change", "NFP_YOY_change", "TNX_change"]
    rows = []
    for fac in factors:
        for lag in range(0, max_lag + 1):
            row = {"factor": fac, "lag_months": lag}
            for sym in ["SPY", "QQQ", "XLF", "XLE", "XLK", "XLU"]:
                f = macro_df[fac].shift(0)
                r = rets_df[sym].shift(-lag)
                sub = pd.concat([f, r], axis=1, keys=[fac, sym]).dropna()
                if len(sub) >= 24:
                    row[sym] = round(float(sub[fac].corr(sub[sym])), 3)
            rows.append(row)
    return pd.DataFrame(rows)


def regime_conditional(rets_df, macro_df):
    """How sectors perform under rising-rate vs falling-rate regimes."""
    ffr_chg = macro_df["FFR_change"]
    # align to the returns index first
    common = rets_df.index.intersection(ffr_chg.dropna().index)
    ffr_a = ffr_chg.reindex(common)
    rets_a = rets_df.reindex(common)
    out = {}
    for label, mask in [
        ("加息(FFR上升)", ffr_a > 0.05),
        ("降息(FFR下降)", ffr_a < -0.05),
        ("利率平稳", (ffr_a >= -0.05) & (ffr_a <= 0.05)),
    ]:
        sub = rets_a.loc[mask]
        out[label] = {}
        for sym, name in SECTORS:
            col = sub[sym].dropna()
            if len(col) >= 6:
                out[label][sym] = {"avg_ret_pct": round(float(col.mean()) * 100, 2),
                                   "win_pct": round(float((col > 0).mean()) * 100, 1),
                                   "n": int(len(col))}
    return out


def rolling_r2(macro_df, rets_df, window=60):
    """Rolling R^2 of macro changes explaining SPY returns (5-factor model)."""
    factors = ["FFR_change", "CPI_YOY_change", "UNEMP_change", "NFP_YOY_change", "TNX_change"]
    df = macro_df[factors].join(rets_df["SPY"]).dropna()
    rows = []
    for i in range(window, len(df)):
        sub = df.iloc[i - window:i]
        X = sub[factors].values
        y = sub["SPY"].values
        # add intercept
        X1 = np.column_stack([np.ones(len(X)), X])
        try:
            beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
            yhat = X1 @ beta
            ss_res = float(np.sum((y - yhat) ** 2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        except Exception:
            r2 = 0.0
        rows.append({"date": str(df.index[i].date()), "rolling_r2": round(r2, 3)})
    return pd.DataFrame(rows)


def main():
    print("loading macro + returns...")
    macro_df = load_macro_monthly()
    rets_df = load_sector_monthly_returns()
    print("  macro months:", len(macro_df), "| sector months:", len(rets_df))

    print("concurrent correlation...")
    cc = concurrent_corr(macro_df, rets_df)
    cc.to_csv(PROC / "macro_concurrent_corr.csv", index=False, encoding="utf-8-sig")
    print(cc.to_string(index=False))

    print("\nimplied response (lagged corr)...")
    lc = lagged_corr(macro_df, rets_df, max_lag=12)
    lc.to_csv(PROC / "macro_lagged_corr_impulse.csv", index=False, encoding="utf-8-sig")
    # print key decay
    for fac in lc["factor"].unique():
        sub = lc[lc["factor"] == fac]
        spy0 = sub[sub["lag_months"] == 0]["SPY"]
        spy0 = spy0.iloc[0] if len(spy0) else "-"
        print("  {}: lag0 SPY corr {}".format(fac, spy0))

    print("\nregime-conditional...")
    rc = regime_conditional(rets_df, macro_df)
    for regime, data in rc.items():
        print("  {}:".format(regime))
        spy_d = data.get("SPY", {})
        print("    SPY avg {}% win {}% (n={})".format(spy_d.get("avg_ret_pct"), spy_d.get("win_pct"), spy_d.get("n")))

    print("\nrolling R^2...")
    r2 = rolling_r2(macro_df, rets_df, window=60)
    r2.to_csv(PROC / "macro_rolling_r2.csv", index=False, encoding="utf-8-sig")
    print("  recent R2:", r2["rolling_r2"].iloc[-1] if len(r2) else "n/a")
    print("  mean R2:", round(float(r2["rolling_r2"].mean()), 3))

    summary = {
        "analysis": "macro factor impact on US equities (monthly, 1999-2026)",
        "concurrent_corr": cc.to_dict(orient="records"),
        "regime_conditional": rc,
        "rolling_r2_mean": round(float(r2["rolling_r2"].mean()), 3),
        "rolling_r2_recent": round(float(r2["rolling_r2"].iloc[-1]), 3) if len(r2) else None,
    }
    (PROC / "macro_impact_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("\nsaved.")


if __name__ == "__main__":
    main()
