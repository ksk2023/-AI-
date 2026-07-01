# -*- coding: utf-8 -*-
"""Generate per-ticker historical-backtest Markdown reports.

For each stock in STOCKS, run src.stock_analysis.analyze(), then write:
  docs/research/<TICKER>/<DATE>_<TICKER>_历史回测分析.md
and dump the structured metrics to:
  docs/research/<TICKER>/<DATE>_<TICKER>_metrics.json

Date-prefixed filenames mean re-runs on future dates never overwrite today's.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import stock_analysis as sa  # noqa: E402

RESEARCH = REPO / "docs" / "research"
RESEARCH.mkdir(parents=True, exist_ok=True)

REPORT_DATE = "2026-07-01"

# (symbol, display_name_cn, market, sector_cn)
STOCKS = [
    ("AAPL",      "苹果",          "US 纳斯达克",   "科技-消费电子"),
    ("MSFT",      "微软",          "US 纳斯达克",   "科技-软件/云"),
    ("NVDA",      "英伟达",        "US 纳斯达克",   "半导体-AI算力"),
    ("GOOGL",     "谷歌(Alphabet A)", "US 纳斯达克", "科技-互联网/广告"),
    ("META",      "Meta",          "US 纳斯达克",   "科技-社交/广告"),
    ("AMZN",      "亚马逊",        "US 纳斯达克",   "科技-电商/云"),
    ("TSLA",      "特斯拉",        "US 纳斯达克",   "汽车/能源/科技"),
    ("MU",        "美光(Micron)",  "US 纳斯达克",   "半导体-存储DRAM/NAND"),
    ("SNDK",      "闪迪(SanDisk)", "US 纳斯达克",   "半导体-存储NAND"),
    ("GLW",       "康宁(Corning)", "US 纽交所",     "特种材料-玻璃/光纤"),
    ("MRVL",      "迈威尔(Marvell)", "US 纳斯达克", "半导体-网络/定制ASIC"),
    ("TSM",       "台积电(ADR)",   "US 纽交所ADR",  "半导体-晶圆代工"),
    ("000660_KS", "SK海力士",      "韩国 KOSPI",    "半导体-存储DRAM/HBM"),
    ("005930_KS", "三星电子",      "韩国 KOSPI",    "半导体-存储+消费电子"),
    ("NOK",       "诺基亚",        "US 纽交所ADR",  "通信设备/网络"),
]

# 2330.TW exists too but user asked for TSMC via TSM ADR primarily; keep ADR.
# Add TW-listed TSMC for completeness of "台积电" research.
STOCKS.append(("2330_TW", "台积电(台湾本股)", "台湾 TWSE", "半导体-晶圆代工"))


def safe_dir_name(symbol):
    return symbol.replace(".", "_")


def fmt_months(season):
    names = {1:"1月",2:"2月",3:"3月",4:"4月",5:"5月",6:"6月",7:"7月",8:"8月",9:"9月",10:"10月",11:"11月",12:"12月"}
    bm = season["best_month"]
    wm = season["worst_month"]
    rows = []
    for m in range(1, 13):
        # keys may be int (in-memory) or str (after JSON round-trip); check both
        d = season["by_month"].get(m) or season["by_month"].get(str(m))
        if d is not None:
            mark = ""
            if m == bm["month"]:
                mark = " ⭐ 最佳"
            elif m == wm["month"]:
                mark = " ⚠ 最差"
            rows.append("| {} | {:+}% | {}/{} |{} |".format(names[m], d["avg_pct"], d["pos_years"], d["total_years"], mark))
    return "\n".join(rows)


def fmt_annual(annual):
    rows = []
    for y in sorted(annual.keys()):
        v = annual[y]
        bar = "🟩" if v > 0 else ("🟥" if v < 0 else "⬜")
        rows.append("| {} | {:+}% | {} |".format(y, v, bar))
    return "\n".join(rows)


def fmt_corr(c):
    if c is None:
        return "无重叠数据"
    return "相关系数 {} ｜ Beta {}（重叠 {} 个交易日）".format(c["corr"], c["beta"], c["overlap_days"])


def fmt_lev(lev):
    if not lev:
        return "（无有效回撤数据）"
    rows = []
    for k in [1.0, 1.5, 2.0, 3.0, 5.0]:
        d = lev.get(str(k)) or lev.get(k)
        if d is None:
            continue
        status = "✅ 活" if d["survives"] else "❌ 爆"
        rows.append("| {}x | {}% | {} |".format(k, d["loss_at_worst_mdd_pct"], status))
    cl = lev.get("critical_leverage", "—")
    return "临界杠杆 **{}x**（1/|MDD|）\n\n| 杠杆 | 历史最坏回撤下损失 | 是否存活 |\n|---|---|---|\n" + "\n".join(rows)


def build_report(r):
    sym = r["symbol"]
    mdd = r["max_drawdown"]
    wl = r["win_loss"]
    L = []
    a = L.append

    a("# {}（{}）历史回测分析报告（{}）\n\n".format(r["display_name"], sym, REPORT_DATE))
    a("> 本报告所有价格与统计量均来自 **Yahoo Finance 复权收盘价**（自动拆股+分红调整），\n")
    a("> 区间为该证券在数据源中可得的全部历史日线。无任何估算或假设，所有数字均可由\n")
    a("> `data/raw/daily_{}.parquet` 与 `src/stock_analysis.py` 复现。\n\n".format(safe_dir_name(sym)))
    a("---\n\n")

    a("## 一、证券概况\n\n")
    a("| 项目 | 内容 |\n|---|---|\n")
    a("| 证券代码 | {} |\n".format(sym))
    a("| 名称 | {} |\n".format(r["display_name"]))
    a("| 市场 | {} |\n".format(r["market"]))
    a("| 行业 | {} |\n".format(r["sector"]))
    a("| 数据源 | Yahoo Finance `adj_close`（复权） |\n")
    a("| 样本区间 | {} → {} |\n".format(r["period_start"], r["period_end"]))
    a("| 交易日数 | {:,} |\n".format(r["trading_days"]))
    a("| 时间跨度 | {} 年 |\n".format(r["span_years"]))
    a("| 起始复权价 | {} |\n".format(r["start_price"]))
    a("| 终止复权价 | {} |\n\n".format(r["end_price"]))

    a("## 二、核心收益与风险指标\n\n")
    a("| 指标 | 数值 |\n|---|---|\n")
    a("| **累计总收益** | **{:+}%** |\n".format(r["total_return_pct"]))
    a("| **年化收益 CAGR** | **{:+}%** |\n".format(r["cagr_pct"]))
    a("| 年化波动率 | {}% |\n".format(r["annualized_vol_pct"]))
    a("| 夏普比率（无风险2%） | {} |\n".format(r["sharpe"]))
    a("| 索提诺比率 | {} |\n\n".format(r["sortino"]))

    a("## 三、最大回撤与恢复\n\n")
    a("| 指标 | 数值 |\n|---|---|\n")
    a("| **历史最大回撤 MDD** | **{}%** |\n".format(mdd["mdd_pct"]))
    a("| 峰值日期 | {} |\n".format(mdd["peak_date"]))
    a("| 谷底日期 | {} |\n".format(mdd["trough_date"]))
    if mdd["recovered"]:
        a("| 恢复至峰值日期 | {} |\n".format(mdd["recovery_date"]))
        a("| **从峰值到恢复** | **{} 天** |\n\n".format(mdd["recovery_days"]))
    else:
        a("| 恢复情况 | **至今未恢复至峰值** |\n\n")

    a("## 四、阴阳平衡（涨跌天数）\n\n")
    a("| 指标 | 数值 |\n|---|---|\n")
    a("| 上涨天数 | {:,} |\n".format(wl["up_days"]))
    a("| 下跌天数 | {:,} |\n".format(wl["down_days"]))
    a("| 平盘天数 | {:,} |\n".format(wl["flat_days"]))
    a("| **上涨天数占比** | **{}%** |\n".format(wl["up_ratio_pct"]))
    a("| 单日最大涨幅 | {:+}% |\n".format(wl["best_day_pct"]))
    a("| 单日最大跌幅 | {:+}% |\n\n".format(wl["worst_day_pct"]))

    a("## 五、月度季节性\n\n")
    a("| 月份 | 平均月收益 | 上涨年数/总年数 | 标记 |\n|---|---|---|---|\n")
    a(fmt_months(r["monthly_seasonality"]))
    a("\n\n")

    a("## 六、逐年收益\n\n")
    a("| 年份 | 年度收益 | | 年份 | 年度收益 | |\n|---|---|---|---|---|---|\n")
    years = sorted(r["annual_returns"].keys())
    # two-column layout
    half = (len(years) + 1) // 2
    left, right = years[:half], years[half:]
    for i in range(half):
        ly = left[i]
        lv = r["annual_returns"][ly]
        lbar = "🟩" if lv > 0 else "🟥"
        if i < len(right):
            ry = right[i]
            rv = r["annual_returns"][ry]
            rbar = "🟩" if rv > 0 else "🟥"
            a("| {} | {:+}% | {} | {} | {:+}% | {} |\n".format(ly, lv, lbar, ry, rv, rbar))
        else:
            a("| {} | {:+}% | {} | | | |\n".format(ly, lv, lbar))
    a("\n")

    a("## 七、滚动 252 日（约一年）窗口\n\n")
    rl = r["rolling_252d"]
    if rl:
        a("| 指标 | 数值 |\n|---|---|\n")
        a("| 窗口最佳累计收益 | {:+}% |\n".format(rl["best_rolling_pct"]))
        a("| 窗口最差累计收益 | {:+}% |\n".format(rl["worst_rolling_pct"]))
        a("| 负收益窗口占比 | {}% |\n\n".format(rl["pct_negative"]))

    a("## 八、与基准相关性\n\n")
    a("| 基准 | 结果 |\n|---|---|\n")
    a("| SPY（标普500） | {} |\n".format(fmt_corr(r["correlation"]["SPY"])))
    a("| QQQ（纳斯达克100） | {} |\n".format(fmt_corr(r["correlation"]["QQQ"])))
    a("| NASDAQ综合指数 | {} |\n\n".format(fmt_corr(r["correlation"]["NASDAQ_COMPOSITE"])))

    a("## 九、杠杆爆仓敏感度（基于历史最坏回撤）\n\n")
    a("用本证券历史最大回撤 {}% 反推：在历史最坏情境下，杠杆放大后的损失如下。\n\n".format(mdd["mdd_pct"]))
    a(fmt_lev(r["leverage_sensitivity"]))
    a("\n\n")

    a("## 十、投资规律小结\n\n")
    a("（基于以上纯数据统计，不含主观预测）\n\n")
    a("1. **长期复利**：{} 年区间累计 {:+}%，CAGR {:+}%。\n".format(r["span_years"], r["total_return_pct"], r["cagr_pct"]))
    a("2. **回撤韧性**：最坏回撤 {}%".format(mdd["mdd_pct"]))
    if mdd["recovered"]:
        a("，用了 {} 天恢复。".format(mdd["recovery_days"]))
    else:
        a("，至今未恢复。")
    a("3. **阴线阳线**：上涨天数占比 {}%，{}。\n".format(wl["up_ratio_pct"], "略偏多头" if wl["up_ratio_pct"] > 50 else "略偏空头或均衡"))
    bm = r["monthly_seasonality"]["best_month"]
    wm = r["monthly_seasonality"]["worst_month"]
    a("4. **季节性**：{} 月平均 {:+}%（{}年{}涨），{} 月平均 {:+}%（{}年{}涨）。\n".format(
        bm["month"], bm["avg_pct"], bm["total_years"], bm["pos_years"],
        wm["month"], wm["avg_pct"], wm["total_years"], wm["pos_years"]))
    cl = r["leverage_sensitivity"].get("critical_leverage", "—")
    a("5. **杠杆风险**：历史最坏回撤对应临界杠杆约 {}x，超过此值在最坏情境下清盘。\n\n".format(cl))

    a("## 附录：可复现性\n\n")
    a("- 数据：`data/raw/daily_{}.parquet`\n".format(safe_dir_name(sym)))
    a("- 分析脚本：`src/stock_analysis.py`\n")
    a("- 结构化指标：`{}/{}_{}_metrics.json`\n".format(safe_dir_name(sym), REPORT_DATE, sym))

    return "".join(L)


def main():
    done = []
    failed = []
    for sym, name, market, sector in STOCKS:
        try:
            print("analyzing", sym, "...")
            r = sa.analyze(sym, name, market, sector)
            d = RESEARCH / safe_dir_name(sym)
            d.mkdir(parents=True, exist_ok=True)
            json_name = "{}_{}_metrics.json".format(REPORT_DATE, sym)
            md_name = "{}_{}_历史回测分析.md".format(REPORT_DATE, sym)
            (d / json_name).write_text(
                json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
            (d / md_name).write_text(build_report(r), encoding="utf-8")
            print("  OK ->", d / md_name)
            done.append(sym)
        except Exception as e:
            import traceback
            print("  FAIL", sym, e)
            traceback.print_exc()
            failed.append((sym, str(e)))
    print("\n{} done, {} failed".format(len(done), len(failed)))
    if failed:
        print("failed:", failed)


if __name__ == "__main__":
    main()
