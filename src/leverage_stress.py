"""杠杆压力测试 + 防御性减仓模拟。

目标: 用 NASDAQ 综合指数 56 年日线真实数据, 评估不同杠杆倍数下的清盘风险,
并测试"动态防御性减仓"机制对存活率的改善。
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(".")
RAW = REPO / "data" / "raw"
PROC = REPO / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)


def load_nasdaq():
    df = pd.read_parquet(RAW / "daily_NASDAQ_COMPOSITE.parquet")
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    return df


def rolling_mdd(series, window):
    """滚动最大回撤: 在 window 日窗口内, 从峰值到谷值的最大跌幅。
    返回: 最大回撤序列(对齐到窗口终点)"""
    s = pd.Series(series).reset_index(drop=True)
    out = pd.Series(np.nan, index=s.index)
    arr = s.values
    n = len(arr)
    for i in range(window, n):
        seg = arr[i - window:i]
        peak = seg[0]
        max_dd = 0.0
        cur_peak = seg[0]
        for v in seg:
            cur_peak = max(cur_peak, v)
            dd = v / cur_peak - 1.0
            if dd < max_dd:
                max_dd = dd
        out.iloc[i] = max_dd
    return out


def leverage_nav_curve(returns: np.ndarray, leverage: float, margin_call: float = 0.0):
    """给定日收益序列与杠杆倍数, 计算 NAV 曲线。
    margin_call: 维持保证金比例 (NAV 跌破此值触发爆仓, 之后 NAV 固定为 0)。
    返回: nav 序列, blowup_idx (首次爆仓位置, 无则 -1)
    """
    nav = np.empty(len(returns) + 1)
    nav[0] = 1.0
    for i, r in enumerate(returns):
        # 杠杆日收益: NAV *= (1 + L*r)
        nav[i + 1] = nav[i] * (1.0 + leverage * r)
        if nav[i + 1] <= margin_call:
            nav[i + 1:] = 0.0
            return nav, i + 1
    return nav, -1


def leverage_with_defense(returns: np.ndarray, leverage: float, vol_window: int = 20,
                           vol_threshold_pct: float = 80, defense_leverage: float = 0.3):
    """动态防御性减仓: 滚动波动率超过历史分位数时, 杠杆从 L 降为 defense_leverage。
    vol_threshold_pct: 触发减仓的滚动波动率百分位 (相对历史所有滚动波动率)。
    """
    nav = np.empty(len(returns) + 1)
    nav[0] = 1.0
    n = len(returns)
    # 预计算滚动波动率
    r = pd.Series(returns)
    rolling_vol = r.rolling(vol_window).std().fillna(0).values
    # 历史百分位阈值 (in-sample, 简化版)
    if len(rolling_vol) > 0:
        threshold = np.percentile(rolling_vol, vol_threshold_pct)
    else:
        threshold = 0.02
    cur_lev = leverage
    for i in range(n):
        if rolling_vol[i] > threshold:
            cur_lev = min(cur_lev, defense_leverage)
        else:
            cur_lev = leverage
        nav[i + 1] = nav[i] * (1.0 + cur_lev * returns[i])
    return nav


def find_fat_tail_events(returns, threshold_pct=10):
    """找出肥尾事件: 单日跌幅 > threshold_pct% 或 2 日累计跌幅 > 2*threshold_pct%。
    返回事件列表: {date, type, ret}
    """
    events = []
    for i, r in enumerate(returns):
        if r <= -threshold_pct / 100:
            events.append({"idx": i, "ret": float(r), "type": "single_day"})
        if i >= 1:
            two_day = (1 + returns[i]) * (1 + returns[i - 1]) - 1
            if two_day <= -2 * threshold_pct / 100 and two_day > r - 0.001:
                # 两日累计,且不是已经记录的单日
                events.append({"idx": i - 1, "ret": float(two_day), "type": "two_day_compound"})
    return events


def main():
    print("loading NASDAQ composite daily history...")
    df = load_nasdaq()
    df["ret"] = df["close"].pct_change().fillna(0)
    returns = df["ret"].values[1:]  # 去掉首日 NaN
    dates = df["date"].values[1:]
    print(f"  total trading days: {len(returns)}")
    print(f"  period: {pd.Timestamp(dates[0]).date()} -> {pd.Timestamp(dates[-1]).date()}")
    print(f"  data source: Yahoo Finance ^IXIC (adj_close)")
    print()

    # ===== 1. 历史最大回撤分析 =====
    print("=== [1] Historical Rolling Max Drawdown ===")
    for window in [252, 756, 1260]:  # 1y, 3y, 5y
        mdd = rolling_mdd(df["close"].values, window)
        valid = mdd.dropna()
        worst = valid.min()
        worst_idx = valid.idxmin()
        worst_date = df["date"].iloc[worst_idx]
        print(f"  rolling {window}d window: worst MDD = {worst*100:.2f}%, ending {worst_date.date()}")
    print()

    # ===== 2. 全期 MDD (买入持有) =====
    cum = (1 + df["ret"]).cumprod()
    peak = cum.cummax()
    dd = cum / peak - 1
    full_mdd = dd.min()
    full_mdd_date = df["date"].iloc[dd.idxmin()]
    print(f"=== [2] Buy-and-Hold Full-Period MDD ===")
    print(f"  worst MDD: {full_mdd*100:.2f}%  (peak -> trough, 1971-2026)")
    print(f"  date: {full_mdd_date.date()}")
    print()

    # ===== 3. 杠杆清盘热力图 =====
    print("=== [3] Leverage Liquidation Heatmap ===")
    # 不同 leverage × 不同维持保证金 (margin_call)
    leverages = [1.0, 1.5, 2.0, 3.0, 5.0]
    margin_calls = [0.20, 0.30, 0.50]  # NAV 跌破 30% 算爆仓等
    rows = []
    for L in leverages:
        for mc in margin_calls:
            nav, blowup_idx = leverage_nav_curve(returns, L, margin_call=mc)
            survived = blowup_idx == -1
            final_nav = nav[-1]
            min_nav = np.min(nav[nav > 0]) if np.any(nav > 0) else 0
            rows.append({
                "leverage": L,
                "margin_call_threshold": mc,
                "survived_full_period": survived,
                "first_blowup_day": int(blowup_idx) if not survived else -1,
                "final_nav_multiple": float(final_nav),
                "min_nav_after_start": float(min_nav),
            })
    hm = pd.DataFrame(rows)
    print(hm.to_string(index=False))
    hm.to_csv(PROC / "leverage_liquidation_heatmap.csv", index=False, encoding="utf-8-sig")
    print()

    # ===== 4. 防御性减仓效果对比 =====
    print("=== [4] Dynamic Defensive Deleveraging vs Fixed Leverage ===")
    cmp_rows = []
    for L in [1.5, 2.0, 3.0, 5.0]:
        nav_fixed, _ = leverage_nav_curve(returns, L, margin_call=0.30)
        nav_def = leverage_with_defense(returns, L, vol_window=20,
                                        vol_threshold_pct=80, defense_leverage=0.3)
        cmp_rows.append({
            "leverage": L,
            "fixed_final_nav": float(nav_fixed[-1]),
            "fixed_min_nav": float(np.min(nav_fixed)),
            "defense_final_nav": float(nav_def[-1]),
            "defense_min_nav": float(np.min(nav_def)),
            "defense_outperformance": float(nav_def[-1] - nav_fixed[-1]),
        })
    df_cmp = pd.DataFrame(cmp_rows)
    print(df_cmp.to_string(index=False))
    df_cmp.to_csv(PROC / "defense_deleveraging_comparison.csv", index=False, encoding="utf-8-sig")
    print()

    # ===== 5. 肥尾事件识别 =====
    print("=== [5] Fat-Tail Events (single-day drop >10% OR 2-day compound >20%) ===")
    events = find_fat_tail_events(returns, threshold_pct=10)
    # 去重 (single-day 比 2-day 更具体)
    seen = set()
    unique = []
    for e in sorted(events, key=lambda x: -abs(x["ret"])):
        if e["idx"] in seen or e["idx"] + 1 in seen:
            continue
        seen.add(e["idx"])
        unique.append(e)
    print(f"  total fat-tail events: {len(unique)}")
    ft_rows = []
    for e in unique[:20]:  # 只列最严重的 20 个
        d = pd.Timestamp(dates[e["idx"]]).date()
        ft_rows.append({
            "date": str(d),
            "type": e["type"],
            "return_pct": round(e["ret"] * 100, 2),
        })
        print(f"  {d}  {e['type']:18s}  {e['ret']*100:+.2f}%")
    pd.DataFrame(ft_rows).to_csv(PROC / "fat_tail_events.csv", index=False, encoding="utf-8-sig")
    print()

    # ===== 6. 总结指标 =====
    summary = {
        "data_source": "Yahoo Finance ^IXIC (NASDAQ Composite), adj_close",
        "period": f"{pd.Timestamp(dates[0]).date()} -> {pd.Timestamp(dates[-1]).date()}",
        "total_trading_days": int(len(returns)),
        "full_period_mdd_pct": round(full_mdd * 100, 2),
        "leverage_survivors": hm.groupby("leverage")["survived_full_period"].sum().to_dict(),
        "fat_tail_events_count": len(unique),
        "defense_improvement_avg": float(df_cmp["defense_outperformance"].mean()),
    }
    with open(PROC / "leverage_stress_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print("summary saved to data/processed/leverage_stress_summary.json")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()