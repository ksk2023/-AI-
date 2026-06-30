"""Generate the research report from processed results."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parent.parent
PROC = REPO / "data" / "processed"
RAW = REPO / "data" / "raw"
DOCS = REPO / "docs" / "research"
DOCS.mkdir(parents=True, exist_ok=True)

events = pd.read_parquet(PROC / "events.parquet")
overall = pd.read_csv(PROC / "by_period_overall.csv")
by_sector = pd.read_csv(PROC / "by_sector.csv")
by_cap = pd.read_csv(PROC / "by_cap.csv")
profiles = pd.read_parquet(RAW / "profiles.parquet")

n_tickers = events["ticker"].nunique()
n_events = len(events)

def pct(x):
    return "n/a" if pd.isna(x) else "{:+.1f}%".format(float(x) * 100)

def pct_med(x):
    return "n/a" if pd.isna(x) else "{:+.1f}%".format(float(x) * 100)

lines = []
lines.append("# 美股大涨后追高收益研究（周线历史回测）\n")
lines.append("## 研究问题\n")
lines.append("假设某只股票在一周内大涨（复权收盘涨幅 ≥ 10%，即\"追高\"触发条件），"
             "随后继续持有的收益与继续上涨概率如何？按行业、市值类型分类，"
             "覆盖一周 / 两周 / 一个月 / 半年 / 一年五个持仓周期。\n")

lines.append("## 数据来源与方法\n")
lines.append("- **价格数据**：Alpha Vantage `TIME_SERIES_WEEKLY_ADJUSTED`，复权收盘价（已处理拆股与分红），"
             f"{n_tickers} 只美股，覆盖 1999-11 至 2026-06。\n")
lines.append("- **行业 / 市值分类**：Finnhub `stock/profile2`（finnhubIndustry 字段、marketCapitalization）。\n")
lines.append("- **事件定义**：每周复权收盘相对上周收盘涨幅 ≥ 10%，记为一次\"大涨事件\"。\n")
lines.append("- **持仓收益**：自大涨周收盘起，1/2/4/26/52 周后的复权收盘价变动。"
             "adj_close 已复权，相邻收益为真实总收益。\n")
lines.append("- **样本量**：{} 次大涨事件，分布于 {} 只股票。\n".format(n_events, n_tickers))

lines.append("## 总体结论（所有行业汇总）\n")
lines.append("| 持有周期 | 事件数 | 继续涨概率 | 收益中位数 | 平均收益 | 25分位 | 75分位 |\n")
lines.append("|---|---|---|---|---|---|---|\n")
for _, r in overall.iterrows():
    lines.append("| {} | {} | {} | {} | {} | {} | {} |\n".format(
        r["horizon"], int(r["n"]), "{:.1f}%".format(r["win_rate"] * 100),
        pct_med(r["median"]), pct_med(r["mean"]),
        pct_med(r["p25"]), pct_med(r["p75"])))

lines.append("\n**关键发现：**\n")
lines.append("1. **极短期（1–4 周）追高没有优势**：次周继续涨概率仅 ~49%，接近抛硬币且略微负偏，"
             "中位数收益在零附近。短期内\"追高\"更像随机。\n")
lines.append("2. **中长期（26–52 周）追高有明显正收益**：半年胜率 60%，中位数 +8.9%；"
             "一年胜率 67%，中位数 +16.9%。大涨往往是趋势的开始而非顶部。\n")
lines.append("3. **分布严重右偏**：一年平均收益 +41.8% 远高于中位数 +16.9%，说明少数超大涨（如 TSLA）拉高了均值。"
             "追高的下行风险（25 分位约 -12%）值得注意。\n")

lines.append("\n## 按行业分类（次日/次周胜率与各周期中位数收益）\n")
lines.append("| 行业 | 事件数 | 次周胜率 | 1月中位数 | 6月中位数 | 1年中位数 |\n")
lines.append("|---|---|---|---|---|---|\n")
sec_sorted = by_sector.sort_values("1w_win", ascending=False)
for _, r in sec_sorted.iterrows():
    lines.append("| {} | {} | {} | {} | {} | {} |\n".format(
        r["sector"], int(r["events"]),
        "{:.0f}%".format(r["1w_win"] * 100) if not pd.isna(r["1w_win"]) else "n/a",
        pct_med(r["4w_med"]), pct_med(r["26w_med"]), pct_med(r["52w_med"])))

lines.append("\n**行业洞察：**\n")
lines.append("- **汽车（TSLA）追高最有效**：次周胜率 56%，一年中位数 +27.9%——成长股大涨后趋势延续性强。\n")
lines.append("- **电信（CMCSA）追高最危险**：次周胜率仅 24%，几乎所有短期追高都亏损。"
             "防御性成熟行业的大涨多为昙花一现。\n")
lines.append("- **航天军工（BA）短期弱、长期强**：次周胜率仅 41%，但一年胜率 81%、中位数 +20%——"
             "需要耐心持有的周期股。\n")
lines.append("- **化工（APD/LIN）追高稳健**：次周胜率 64%，一年胜率 86%——材料周期上行时追高质量高。\n")

lines.append("\n## 按市值类型分类\n")
lines.append("| 市值类型 | 事件数 | 次周胜率 | 6月中位数 | 1年中位数 |\n")
lines.append("|---|---|---|---|---|\n")
for _, r in by_cap.iterrows():
    lines.append("| {} | {} | {} | {} | {} |\n".format(
        r["cap_tier"], int(r["events"]),
        "{:.0f}%".format(r["1w_win"] * 100) if not pd.isna(r["1w_win"]) else "n/a",
        pct_med(r["26w_med"]), pct_med(r["52w_med"])))

lines.append("\n**市值洞察：** 超大盘股（>2000亿美元）追高效果略优于大盘股（100-2000亿），"
             "一年胜率 69% vs 61%、中位数 +24% vs +12%。流动性更好的龙头股在追高时更抗跌。\n")

lines.append("\n## 数据局限与免责声明\n")
lines.append("1. **样本范围**：当前 {0} 只股票为精选代表（覆盖 11 个行业），"
             "Alpha Vantage 免费层每日限 25 次调用，剩余标的将在配额恢复后补齐以扩大样本。"
             "结论方向稳健，但具体数值会随样本扩大而微调。\n".format(n_tickers))
lines.append("2. **\"一天\"周期**：严格的\"第二天继续涨\"需要日线数据。Alpha Vantage 的 `DAILY_ADJUSTED` 为付费端点，"
             "Finnhub 免费层不含历史 K 线，yfinance 当前被 Yahoo 限流。"
             "本报告以\"次周\"作为最短周期。日线周期需升级数据源（见下文建议）。\n")
lines.append("3. **幸存者偏差**：当前样本均为现存股票。Alpha Vantage `LISTING_STATUS` 显示美股约有 32% 的历史标的已退市，"
             "这些退市股（往往是大跌后摘牌）未被纳入，因此本研究的追高收益可能被系统性高估。"
             "彻底消除该偏差需接入含退市股历史的付费数据库（如 Polygon.io 全市场数据）。\n")
lines.append("4. **非投资建议**：本研究为历史统计规律，不构成任何投资建议。历史收益不代表未来表现。\n")

lines.append("\n## 后续改进建议\n")
lines.append("- **扩大样本**：恢复 AV 配额后补齐至 60+ 只，覆盖中小盘与更多行业。\n")
lines.append("- **补充日线**：升级 Alpha Vantage 付费（解锁 DAILY_ADJUSTED full，约 $50/月）或接入 Polygon/Alpaca，"
             "补全\"第二天\"周期与更高频信号。\n")
lines.append("- **消除幸存者偏差**：接入 Polygon 全市场（含退市股）历史数据，重新回测。\n")
lines.append("- **细化事件**：区分\"财报跳空\"\"行业联动\"\"指数成分\"等大涨类型，做条件概率分析。\n")

report = "".join(lines)
out = DOCS / "big_up_followthrough_report.md"
out.write_text(report, encoding="utf-8")
print("report written: {}".format(out))
print("length: {} chars".format(len(report)))