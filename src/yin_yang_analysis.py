"""美股阴阳平衡假设分析: 纳斯达克综合指数逐年上涨/下跌/平盘天数。

数据来源: Yahoo Finance ^IXIC 纳斯达克综合指数复权收盘价, 1971-02-05 起。
定义: 收盘价 vs 前一交易日收盘价 (close-to-close)。
"""
import pandas as pd
import numpy as np
from pathlib import Path

REPO = Path(".")
RAW = REPO / "data" / "raw"
PROC = REPO / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(RAW / "daily_NASDAQ_COMPOSITE.parquet")
df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
df = df.sort_values("date").reset_index(drop=True)

# daily close-to-close return
df["ret"] = df["close"].pct_change()
df["dir"] = np.where(df["ret"] > 0, "up", np.where(df["ret"] < 0, "down", "flat"))
df["year"] = df["date"].dt.year

# the first row has NaN return (no prior day) - exclude it
df = df.dropna(subset=["ret"]).copy()

# annual aggregation
rows = []
for yr, g in df.groupby("year"):
    n = len(g)
    up = (g["dir"] == "up").sum()
    down = (g["dir"] == "down").sum()
    flat = (g["dir"] == "flat").sum()
    up_pct = up / n * 100
    down_pct = down / n * 100
    ratio = up / down if down > 0 else float("inf")
    # deviation from 1:1 (absolute percentage point gap)
    deviation = abs(up_pct - down_pct)
    annual_ret = (g.iloc[-1]["close"] / g.iloc[0]["close"] - 1) * 100
    start = g["date"].min().date()
    end = g["date"].max().date()
    rows.append({
        "year": int(yr),
        "trading_days": int(n),
        "up_days": int(up),
        "down_days": int(down),
        "flat_days": int(flat),
        "up_pct": round(up_pct, 2),
        "down_pct": round(down_pct, 2),
        "up_down_ratio": round(ratio, 4),
        "deviation_from_1to1_pct": round(deviation, 2),
        "annual_return_pct": round(annual_ret, 2),
        "start_date": str(start),
        "end_date": str(end),
    })

result = pd.DataFrame(rows)
result.to_csv(PROC / "nasdaq_yin_yang_balance.csv", index=False, encoding="utf-8-sig")
print("saved data/processed/nasdaq_yin_yang_balance.csv")
print(f"\ntotal years: {len(result)}")
print(f"total trading days analyzed: {result['trading_days'].sum()}")
print(f"total up days: {result['up_days'].sum()}")
print(f"total down days: {result['down_days'].sum()}")
print(f"overall up/down ratio: {result['up_days'].sum()/result['down_days'].sum():.4f}")

# statistics
avg_dev = result["deviation_from_1to1_pct"].mean()
years_close = (result["deviation_from_1to1_pct"] <= 2).sum()
years_far = (result["deviation_from_1to1_pct"] > 5).sum()
print(f"\n=== 阴阳平衡检验 ===")
print(f"平均偏离1:1的程度: {avg_dev:.2f} 个百分点")
print(f"非常接近1:1 (偏离<=2pp) 的年份: {years_close}/{len(result)}")
print(f"严重偏离1:1 (偏离>5pp) 的年份: {years_far}/{len(result)}")

# worst and best years
print(f"\n最不平衡的5年 (偏离最大):")
w = result.nlargest(5, "deviation_from_1to1_pct")
for _,r in w.iterrows():
    print(f"  {r['year']}: 涨{r['up_days']}天({r['up_pct']}%) 跌{r['down_days']}天({r['down_pct']}%) 年涨跌{r['annual_return_pct']:+.1f}%")

print(f"\n最接近1:1的5年:")
b = result.nsmallest(5, "deviation_from_1to1_pct")
for _,r in b.iterrows():
    print(f"  {r['year']}: 涨{r['up_days']}天({r['up_pct']}%) 跌{r['down_days']}天({r['down_pct']}%) 年涨跌{r['annual_return_pct']:+.1f}%")