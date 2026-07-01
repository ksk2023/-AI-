# -*- coding: utf-8 -*-
"""Monthly macro-state and sector-rotation analysis (v2 with bonds).

Macro regime per month derived from THREE signals:
  1. VIX level (relative to its own history percentile)
  2. 10Y treasury yield trend (TNX month avg vs its history)
  3. Defensive (XLU+XLP) vs Cyclical (XLY+XLI+XLB) leadership

Sector rotation: per-month average return, win rate, excess vs SPY.
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
PROC.mkdir(parents=True, exist_ok=True)

MONTH_NAMES = {m: "{}月".format(m) for m in range(1, 13)}

ASSETS = [
    ("SPY", "标普500", "大盘", True),
    ("QQQ", "纳斯达克100", "大盘", True),
    ("DIA", "道琼斯", "大盘", True),
    ("IWM", "罗素2000小盘", "大盘", True),
    ("XLK", "科技", "行业-成长", True),
    ("XLV", "医疗保健", "行业-防御", True),
    ("XLF", "金融", "行业-周期", True),
    ("XLE", "能源", "行业-周期", True),
    ("XLY", "可选消费", "行业-周期", True),
    ("XLP", "必需消费", "行业-防御", True),
    ("XLI", "工业", "行业-周期", True),
    ("XLU", "公用事业", "行业-防御", True),
    ("XLB", "材料", "行业-周期", True),
    ("XLRE", "房地产", "行业-利率敏感", False),
    ("XLC", "通信", "行业-成长", False),
]

BOND_ASSETS = [
    ("xTNX", "10年期国债收益率", "利率"),
    ("TLT", "20+年国债ETF", "长久期债券"),
    ("AGG", "综合债券ETF", "债券"),
]

CYCLICAL = ["XLY", "XLI", "XLB", "XLF", "XLE"]
DEFENSIVE = ["XLU", "XLP", "XLV"]


def load_px(symbol):
    f = RAW / "daily_{}.parquet".format(symbol)
    df = pd.read_parquet(f)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    df["px"] = df["adj_close"].fillna(df["close"])
    return df


def monthly_returns(df):
    s = df.set_index("date")["px"]
    monthly = s.resample("ME").last()
    rets = monthly.pct_change().dropna()
    return pd.DataFrame({"year": rets.index.year, "month": rets.index.month, "ret": rets.values})


def monthly_avg_level(df):
    """Monthly average of a LEVEL series (used for VIX, TNX yields)."""
    s = df.set_index("date")["px"]
    monthly = s.resample("ME").mean().dropna()
    return pd.DataFrame({"year": monthly.index.year, "month": monthly.index.month, "level": monthly.values})


def pct_rank(value, series):
    arr = np.asarray(series)
    return float((arr <= value).sum() / len(arr))


def classify_regime(vix_pct, tnx_trend, cyc_def_gap):
    """Three-signal macro regime classification."""
    # risk appetite from VIX percentile
    if vix_pct < 0.35:
        risk = "risk-on"
    elif vix_pct > 0.65:
        risk = "risk-off"
    else:
        risk = "neutral"
    # growth/defensive leadership
    if cyc_def_gap > 0.5:
        leadership = "周期股领涨(经济扩张/再通胀)"
    elif cyc_def_gap < -0.5:
        leadership = "防御股领涨(避险/防御)"
    else:
        leadership = "均衡"
    # combine
    if risk == "risk-on" and "周期" in leadership:
        return "扩张(适合进攻:周期+成长)", leadership
    if risk == "risk-off" and "防御" in leadership:
        return "收缩(适合防御:公用事业+必需消费+债券)", leadership
    if risk == "risk-on" and "防御" in leadership:
        return "分化(低波动但资金避险)", leadership
    if risk == "risk-off" and "周期" in leadership:
        return "反转(恐慌中抄底周期)", leadership
    return "中性(均衡配置)", leadership


def analyze():
    all_monthly = None
    meta = {}
    for sym, name, group, full in ASSETS:
        df = load_px(sym)
        m = monthly_returns(df).rename(columns={"ret": sym})
        meta[sym] = {"name": name, "group": group, "full": full,
                     "start": str(df["date"].min().date()),
                     "end": str(df["date"].max().date()), "years": len(m)}
        if all_monthly is None:
            all_monthly = m[["year", "month", sym]]
        else:
            all_monthly = all_monthly.merge(m[["year", "month", sym]], on=["year", "month"], how="outer")
    all_monthly = all_monthly.sort_values(["year", "month"]).reset_index(drop=True)

    # bonds
    bond_monthly = {}
    bond_meta = {}
    for sym, name, group in BOND_ASSETS:
        df = load_px(sym)
        if sym in ("xTNX",):
            m = monthly_avg_level(df).rename(columns={"level": sym})
            bond_meta[sym] = {"name": name, "start": str(df["date"].min().date()), "end": str(df["date"].max().date())}
        else:
            m = monthly_returns(df).rename(columns={"ret": sym})
            bond_meta[sym] = {"name": name, "start": str(df["date"].min().date()), "end": str(df["date"].max().date())}
        bond_monthly[sym] = m
        all_monthly = all_monthly.merge(m[["year", "month", sym]], on=["year", "month"], how="outer")

    # VIX
    vix = load_px("xVIX")
    vix_monthly = monthly_avg_level(vix).rename(columns={"level": "VIX"})
    all_monthly = all_monthly.merge(vix_monthly[["year", "month", "VIX"]], on=["year", "month"], how="outer")

    # global VIX percentile reference (whole history)
    vix_all = vix_monthly["VIX"].dropna().values
    tnx_all = all_monthly["xTNX"].dropna().values

    results = {}
    for month in range(1, 13):
        sub = all_monthly[all_monthly["month"] == month]
        month_data = {"month": month, "month_name": MONTH_NAMES[month]}

        avg = {}; winrate = {}; excess = {}
        for sym, name, group, full in ASSETS:
            col = sub[sym].dropna()
            if len(col) < 3:
                continue
            avg[sym] = float(col.mean())
            winrate[sym] = float((col > 0).mean())
            if sym != "SPY" and "SPY" in sub.columns:
                pair = sub[["SPY", sym]].dropna().reset_index(drop=True)
                if len(pair) >= 3:
                    excess[sym] = float((pair[sym].values - pair["SPY"].values).mean())

        # cyclical vs defensive composite
        cyc = [avg.get(s) for s in CYCLICAL if s in avg]
        deff = [avg.get(s) for s in DEFENSIVE if s in avg]
        cyc_avg = float(np.mean(cyc)) if cyc else 0.0
        def_avg = float(np.mean(deff)) if deff else 0.0
        cyc_def_gap = round((cyc_avg - def_avg) * 100, 2)

        # macro signals
        vix_month_vals = sub["VIX"].dropna()
        vix_mean = float(vix_month_vals.mean()) if len(vix_month_vals) else None
        vix_pct = pct_rank(vix_mean, vix_all) if vix_mean is not None else None

        tnx_vals = sub["xTNX"].dropna()
        tnx_mean = float(tnx_vals.mean()) if len(tnx_vals) else None
        tnx_pct = pct_rank(tnx_mean, tnx_all) if tnx_mean is not None else None

        regime, leadership = classify_regime(
            vix_pct if vix_pct is not None else 0.5,
            tnx_pct if tnx_pct is not None else 0.5,
            cyc_def_gap)

        # bond returns this month
        bond_rets = {}
        for sym, name, group in BOND_ASSETS:
            if sym == "xTNX":
                continue
            col = sub[sym].dropna()
            if len(col) >= 3:
                bond_rets[sym] = float(col.mean())

        # rank full-history assets
        full_avg = {s: v for s, v in avg.items() if any(s == a[0] and a[3] for a in ASSETS)}
        ranked = sorted(full_avg.items(), key=lambda kv: kv[1], reverse=True)

        month_data.update({
            "avg_return_pct": {s: round(v * 100, 2) for s, v in avg.items()},
            "win_rate_pct": {s: round(v * 100, 1) for s, v in winrate.items()},
            "excess_vs_spy_pct": {s: round(v * 100, 2) for s, v in excess.items()},
            "cyclical_avg_pct": round(cyc_avg * 100, 2),
            "defensive_avg_pct": round(def_avg * 100, 2),
            "cyc_def_gap_pct": cyc_def_gap,
            "leadership": leadership,
            "vix_avg": round(vix_mean, 2) if vix_mean else None,
            "vix_percentile": round(vix_pct * 100, 1) if vix_pct is not None else None,
            "tnx_avg": round(tnx_mean, 2) if tnx_mean else None,
            "tnx_percentile": round(tnx_pct * 100, 1) if tnx_pct is not None else None,
            "macro_regime": regime,
            "bond_returns_pct": {s: round(v * 100, 2) for s, v in bond_rets.items()},
            "best_sector": ranked[0][0] if ranked else None,
            "best_sector_name": next((a[1] for a in ASSETS if a[0] == ranked[0][0]), None) if ranked else None,
            "best_sector_ret": round(ranked[0][1] * 100, 2) if ranked else None,
            "worst_sector": ranked[-1][0] if ranked else None,
            "worst_sector_name": next((a[1] for a in ASSETS if a[0] == ranked[-1][0]), None) if ranked else None,
            "worst_sector_ret": round(ranked[-1][1] * 100, 2) if ranked else None,
            "spy_avg_pct": round(avg.get("SPY", 0) * 100, 2),
            "spy_win_pct": round(winrate.get("SPY", 0) * 100, 1),
        })
        results[month] = month_data
    return results, all_monthly, meta, bond_meta


def main():
    results, all_monthly, meta, bond_meta = analyze()
    all_monthly.to_csv(PROC / "monthly_returns_all_assets.csv", index=False, encoding="utf-8-sig")

    rows = []
    for month in range(1, 13):
        m = results[month]
        row = {"月份": m["month_name"]}
        row["SPY平均%"] = m["spy_avg_pct"]
        row["SPY胜率%"] = m["spy_win_pct"]
        row["VIX均值"] = m.get("vix_avg")
        row["VIX分位%"] = m.get("vix_percentile")
        row["10Y国债%"] = m.get("tnx_avg")
        row["周期-防御差%"] = m.get("cyc_def_gap_pct")
        row["宏观状态"] = m.get("macro_regime")
        row["最佳板块"] = m.get("best_sector_name")
        row["最佳收益%"] = m.get("best_sector_ret")
        row["最差板块"] = m.get("worst_sector_name")
        row["最差收益%"] = m.get("worst_sector_ret")
        rows.append(row)
    pd.DataFrame(rows).to_csv(PROC / "monthly_macro_sector_summary.csv", index=False, encoding="utf-8-sig")

    summary = {"assets": meta, "bonds": bond_meta,
               "months": {str(k): v for k, v in results.items()}}
    (PROC / "monthly_macro_sector.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("saved. months:", len(results))
    print("\n月度宏观+板块速览:")
    for month in range(1, 13):
        m = results[month]
        print("  {:<4} VIX分位{:>4}% 周期-防御{:>+6}% | {:<28} | 最佳{} {:+}% 最差{} {:+}%".format(
            m["month_name"],
            m.get("vix_percentile", "-"),
            m.get("cyc_def_gap_pct", "-"),
            m.get("macro_regime", "")[:28],
            m.get("best_sector_name", "-"), m.get("best_sector_ret", 0),
            m.get("worst_sector_name", "-"), m.get("worst_sector_ret", 0)))


if __name__ == "__main__":
    main()
