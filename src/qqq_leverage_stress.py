"""QQQ 杠杆与回撤爆仓分析。

基于 Invesco QQQ Trust (追踪 NASDAQ-100) 27 年完整日线真实数据。
重点: 杠杆倍数 × 最大回撤 -> 爆仓临界分析 + 日常波动参考。
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(".")
RAW = REPO / "data" / "raw"
PROC = REPO / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)


def load_qqq():
    df = pd.read_parquet(RAW / "daily_QQQ.parquet")
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    df["ret"] = df["close"].pct_change().fillna(0)
    return df


def rolling_mdd(close, window):
    """滚动最大回撤 (peak-to-trough)"""
    s = pd.Series(close)
    arr = s.values
    n = len(arr)
    out = np.full(n, np.nan)
    for i in range(window, n):
        seg = arr[i - window:i]
        peak = seg[0]
        max_dd = 0.0
        for v in seg:
            peak = max(peak, v)
            dd = v / peak - 1.0
            if dd < max_dd:
                max_dd = dd
        out[i] = max_dd
    return pd.Series(out, index=s.index)


def full_period_mdd(close):
    arr = pd.Series(close)
    peak = arr.cummax()
    dd = arr / peak - 1
    return float(dd.min()), int(dd.idxmin())


def leverage_nav(returns, leverage, margin_call=0.20):
    """杠杆 NAV 曲线, NAV 跌破维持保证金则爆仓"""
    nav = np.empty(len(returns) + 1)
    nav[0] = 1.0
    for i, r in enumerate(returns):
        nav[i + 1] = nav[i] * (1.0 + leverage * r)
        if nav[i + 1] <= margin_call:
            nav[i + 1:] = 0.0
            return nav, i + 1
    return nav, -1


def defensive_leverage(returns, leverage, vol_window=20, vol_pct=80, defense_lev=0.3):
    """防御性减仓: 波动率超历史分位时降杠杆"""
    vol = pd.Series(returns).rolling(vol_window).std().fillna(0).values
    threshold = np.percentile(vol, vol_pct) if len(vol) > 0 else 0.02
    nav = np.empty(len(returns) + 1)
    nav[0] = 1.0
    cur = leverage
    for i, r in enumerate(returns):
        if vol[i] > threshold:
            cur = min(cur, defense_lev)
        else:
            cur = leverage
        nav[i + 1] = nav[i] * (1.0 + cur * r)
    return nav


def find_extreme_events(returns, dates, single_day_pct=10, multi_day_pct=15, multi_window=2):
    """肥尾事件: 单日 > threshold% OR N 日累计 > threshold%"""
    events = []
    for i in range(len(returns)):
        if returns[i] <= -single_day_pct / 100:
            events.append({
                "date": str(pd.Timestamp(dates[i]).date()),
                "type": f"single_day_drop<={single_day_pct}%",
                "ret_pct": round(float(returns[i]) * 100, 2),
            })
    for i in range(multi_window, len(returns)):
        cum = (1 + returns[i - multi_window + 1:i + 1]).prod() - 1
        if cum <= -multi_day_pct / 100:
            events.append({
                "date": str(pd.Timestamp(dates[i - multi_window + 1]).date()),
                "type": f"{multi_window}d_compound<{multi_day_pct}%",
                "ret_pct": round(float(cum) * 100, 2),
            })
    # 去重按日期排序
    seen = set()
    out = []
    for e in sorted(events, key=lambda x: x["ret_pct"]):
        if e["date"] not in seen:
            seen.add(e["date"])
            out.append(e)
    return out


def main():
    print("loading QQQ daily history...")
    df = load_qqq()
    returns = df["ret"].values[1:]
    dates = df["date"].values[1:]
    print(f"  total trading days: {len(returns)}")
    print(f"  period: {pd.Timestamp(dates[0]).date()} -> {pd.Timestamp(dates[-1]).date()}")
    print(f"  data source: Yahoo Finance QQQ (adj_close)")
    print()

    # ===== 1. 历史最大回撤 (买入持有全期) =====
    print("=== [1] QQQ Buy-and-Hold Full-Period Max Drawdown ===")
    full_mdd, mdd_idx = full_period_mdd(df["close"].values)
    print(f"  worst MDD: {full_mdd*100:.2f}%  (trough at {df['date'].iloc[mdd_idx].date()})")
    # 找到 peak 日期
    peak_idx = df["close"].iloc[:mdd_idx + 1].idxmax()
    print(f"  peak before trough: {df['date'].iloc[peak_idx].date()}  close={df['close'].iloc[peak_idx]:.2f}")
    print(f"  recovery date: 后续指数涨回峰值的时间")
    # 计算恢复时间
    peak_price = df["close"].iloc[peak_idx]
    after_trough = df["close"].iloc[mdd_idx:]
    rec_idx = after_trough[after_trough >= peak_price].index.min() if (after_trough >= peak_price).any() else None
    if rec_idx:
        rec_date = df["date"].iloc[rec_idx]
        print(f"  recovery: {rec_date.date()}  ({df['date'].iloc[rec_idx].date()}  -> {(rec_date - df['date'].iloc[peak_idx]).days} days from peak)")
    else:
        print(f"  recovery: 至今未恢复")
    print()

    # ===== 2. 滚动窗口 MDD =====
    print("=== [2] Rolling Window MDD (worst in 27y) ===")
    rows = []
    for w in [21, 63, 126, 252, 504, 756, 1260, 1890]:
        mdd_s = rolling_mdd(df["close"].values, w)
        valid = mdd_s.dropna()
        worst = float(valid.min())
        worst_idx = int(valid.idxmin())
        worst_date = df["date"].iloc[worst_idx]
        rows.append({"window_days": w, "window_label": f"{w}d (~{w/252:.1f}y)",
                     "worst_mdd_pct": round(worst * 100, 2), "worst_end_date": str(worst_date.date())})
        print(f"  {w:5d}d (~{w/252:.1f}y): worst MDD = {worst*100:7.2f}%  (window ending {worst_date.date()})")
    pd.DataFrame(rows).to_csv(PROC / "qqq_rolling_mdd.csv", index=False, encoding="utf-8-sig")
    print()

    # ===== 3. 杠杆 × 回撤 爆仓临界矩阵 =====
    print("=== [3] Leverage x MDD -> Liquidation Matrix ===")
    print("    公式: NAV_loss = leverage * MDD. 爆仓条件: NAV_loss >= (1 - margin_call)")
    leverages = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    margin_calls = [0.10, 0.20, 0.30, 0.50]
    matrix = []
    print(f"    用 QQQ 历史最坏 MDD = {full_mdd*100:.2f}% 反推:")
    print()
    print(f"    {'杠杆':<6} | " + " | ".join(f"MC={mc:.0%}" for mc in margin_calls))
    print("    " + "-" * 60)
    for L in leverages:
        line = f"    {L:<6.2f} | "
        cells = []
        for mc in margin_calls:
            # 杠杆放大损失
            leveraged_loss = L * abs(full_mdd)
            blowup = leveraged_loss >= (1 - mc)
            cells.append(f"{leveraged_loss*100:5.1f}% {'X' if blowup else 'OK'}")
        line += " | ".join(cells)
        print(line)
        for mc in margin_calls:
            leveraged_loss = L * abs(full_mdd)
            blowup = leveraged_loss >= (1 - mc)
            matrix.append({
                "leverage": L,
                "margin_call": mc,
                "leveraged_loss_at_worst_mdd_pct": round(leveraged_loss * 100, 2),
                "blowup": bool(blowup),
            })
    pd.DataFrame(matrix).to_csv(PROC / "qqq_leverage_mdd_matrix.csv", index=False, encoding="utf-8-sig")
    print()

    # ===== 4. 实际 NAV 模拟 =====
    print("=== [4] QQQ Leverage NAV Simulation (full 27y history) ===")
    print(f"    {'杠杆':<6} | {'MC=20%':<20} | {'MC=30%':<20} | {'MC=50%':<20}")
    print("    " + "-" * 70)
    nav_rows = []
    for L in leverages:
        line = f"    {L:<6.2f} | "
        cells = []
        for mc in [0.20, 0.30, 0.50]:
            nav, blowup_idx = leverage_nav(returns, L, margin_call=mc)
            survived = blowup_idx == -1
            final = float(nav[-1])
            min_n = float(np.min(nav[nav > 0])) if np.any(nav > 0) else 0.0
            blowup_date = str(pd.Timestamp(dates[blowup_idx]).date()) if not survived else "n/a"
            cells.append(f"{'OK' if survived else 'BLOW'} f={final:.2e}")
            nav_rows.append({
                "leverage": L, "margin_call": mc,
                "survived": survived, "final_nav": final,
                "min_nav_after_start": min_n,
                "blowup_date": blowup_date,
            })
        line += " | ".join(cells)
        print(line)
    pd.DataFrame(nav_rows).to_csv(PROC / "qqq_leverage_nav_simulation.csv", index=False, encoding="utf-8-sig")
    print()

    # ===== 5. 日常波动分布 (非极端情况) =====
    print("=== [5] QQQ Daily Volatility Distribution (normal regime) ===")
    # 排除极端日 (|ret| > 5%)
    normal_mask = np.abs(returns) <= 0.05
    normal_rets = returns[normal_mask]
    print(f"  normal days (|ret| <= 5%): {len(normal_rets)} / {len(returns)} ({len(normal_rets)/len(returns)*100:.1f}%)")
    print(f"  mean daily ret: {normal_rets.mean()*100:.4f}%")
    print(f"  daily std (vol): {normal_rets.std()*100:.4f}%")
    print(f"  annualized vol: {normal_rets.std()*np.sqrt(252)*100:.2f}%")
    print(f"  VaR 95% (daily): {np.percentile(normal_rets, 5)*100:.2f}%")
    print(f"  VaR 99% (daily): {np.percentile(normal_rets, 1)*100:.2f}%")
    print(f"  CVaR 95% (daily, 预期最坏 5% 的平均损失): {normal_rets[normal_rets <= np.percentile(normal_rets, 5)].mean()*100:.2f}%")
    print(f"  CVaR 99% (daily): {normal_rets[normal_rets <= np.percentile(normal_rets, 1)].mean()*100:.2f}%")
    # 5 日累计波动
    cum_5d = []
    for i in range(len(returns) - 5):
        cum_5d.append((1 + returns[i:i+5]).prod() - 1)
    cum_5d = np.array(cum_5d)
    print()
    print(f"  5-day cumulative VaR 95%: {np.percentile(cum_5d, 5)*100:.2f}%")
    print(f"  5-day cumulative VaR 99%: {np.percentile(cum_5d, 1)*100:.2f}%")
    print()

    # ===== 6. 肥尾事件 =====
    print("=== [6] QQQ Extreme Events (single day >10% OR 2-day >15%) ===")
    ext_events = find_extreme_events(returns, dates, single_day_pct=10, multi_day_pct=15, multi_window=2)
    print(f"  total events: {len(ext_events)}")
    for e in ext_events[:30]:
        print(f"  {e['date']}  {e['type']:25s}  {e['ret_pct']:+.2f}%")
    pd.DataFrame(ext_events).to_csv(PROC / "qqq_extreme_events.csv", index=False, encoding="utf-8-sig")
    print()

    # ===== 7. 防御性减仓效果 =====
    print("=== [7] Defensive Deleveraging on QQQ ===")
    cmp_rows = []
    print(f"    {'杠杆':<6} | {'固定终值':<15} | {'防御终值':<15} | {'最低NAV':<10} | {'改进':<15}")
    print("    " + "-" * 70)
    for L in [1.5, 2.0, 3.0, 5.0]:
        nav_fixed, _ = leverage_nav(returns, L, margin_call=0.30)
        nav_def = defensive_leverage(returns, L, vol_window=20, vol_pct=80, defense_lev=0.3)
        cmp_rows.append({
            "leverage": L,
            "fixed_final_nav": float(nav_fixed[-1]),
            "defense_final_nav": float(nav_def[-1]),
            "defense_min_nav": float(np.min(nav_def)),
            "improvement_ratio": float(nav_def[-1] / max(nav_fixed[-1], 1e-30)),
        })
        print(f"    {L:<6.2f} | {nav_fixed[-1]:<15.2e} | {nav_def[-1]:<15.2e} | {np.min(nav_def):<10.4f} | {nav_def[-1]/max(nav_fixed[-1],1e-30):<15.2e}")
    pd.DataFrame(cmp_rows).to_csv(PROC / "qqq_defensive_leverage.csv", index=False, encoding="utf-8-sig")
    print()

    # ===== 总结 =====
    summary = {
        "data_source": "Yahoo Finance QQQ (Invesco QQQ Trust, NASDAQ-100 ETF), adj_close",
        "period": f"{pd.Timestamp(dates[0]).date()} -> {pd.Timestamp(dates[-1]).date()}",
        "total_trading_days": int(len(returns)),
        "full_period_mdd_pct": round(full_mdd * 100, 2),
        "daily_vol_annualized_pct": round(float(normal_rets.std() * np.sqrt(252) * 100), 2),
        "var_95_daily_pct": round(float(np.percentile(normal_rets, 5) * 100), 2),
        "var_99_daily_pct": round(float(np.percentile(normal_rets, 1) * 100), 2),
        "extreme_events_count": len(ext_events),
    }
    with open(PROC / "qqq_leverage_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print("summary saved")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
