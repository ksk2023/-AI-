# -*- coding: utf-8 -*-
"""Generate the monthly macro-state & sector-rotation research report."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROC = REPO / "data" / "processed"
DOCS = REPO / "docs" / "research"
DOCS.mkdir(parents=True, exist_ok=True)
DATE = "2026-07-01"

data = json.loads((PROC / "monthly_macro_sector.json").read_text(encoding="utf-8"))
ASSETS = [
    ("SPY", "标普500", "大盘"), ("QQQ", "纳斯达克100", "大盘"), ("DIA", "道琼斯", "大盘"),
    ("IWM", "罗素2000", "小盘"), ("XLK", "科技", "成长"), ("XLV", "医疗", "防御"),
    ("XLF", "金融", "周期"), ("XLE", "能源", "周期"), ("XLY", "可选消费", "周期"),
    ("XLP", "必需消费", "防御"), ("XLI", "工业", "周期"), ("XLU", "公用事业", "防御"),
    ("XLB", "材料", "周期"), ("XLRE", "房地产", "利率敏感", False), ("XLC", "通信", "成长", False),
]


def macro_portrait(m):
    """Human, data-driven macro reading for a month."""
    spy = m["spy_avg_pct"]; swr = m["spy_win_pct"]
    gap = m.get("cyc_def_gap_pct", 0)
    vix_pct = m.get("vix_percentile", 50)
    best = m.get("best_sector_name"); best_ret = m.get("best_sector_ret", 0)
    worst = m.get("worst_sector_name"); worst_ret = m.get("worst_sector_ret", 0)
    bond = m.get("bond_returns_pct", {})
    tlt = bond.get("TLT", 0)

    parts = []
    # overall direction
    if spy >= 1.5 and swr >= 65:
        parts.append("历史强势月份(SPY 平均 {:+}%, 胜率 {}%)".format(spy, swr))
    elif spy <= -0.5:
        parts.append("历史弱势月份(SPY 平均 {:+}%, 胜率仅 {}%)".format(spy, swr))
    else:
        parts.append("历史震荡月份(SPY 平均 {:+}%, 胜率 {}%)".format(spy, swr))

    # risk appetite via VIX percentile
    if vix_pct >= 65:
        parts.append("VIX 偏高(分位 {}%),市场波动加大".format(vix_pct))
    elif vix_pct <= 50:
        parts.append("VIX 偏低(分位 {}%),风险偏好升温".format(vix_pct))

    # style leadership
    if gap >= 0.8:
        parts.append("周期股明显跑赢防御股({:+}%),资金进攻周期板块".format(gap))
    elif gap <= -0.5:
        parts.append("防御股跑赢周期股({:+}%),资金避险".format(gap))

    # bonds
    if tlt >= 1.0:
        parts.append("长债上涨({:+}%),避险/降息预期升温".format(tlt))
    elif tlt <= -1.0:
        parts.append("长债下跌({:+}%),抛债买股 risk-on".format(tlt))

    # investability verdict
    if spy >= 1.0 and swr >= 65:
        verdict = "适合投资(高胜率正收益)"
    elif spy <= -0.5:
        verdict = "谨慎(历史平均亏损)"
    else:
        verdict = "中性(收益波动大)"

    return "；".join(parts), verdict


def fmt_sector_table(m):
    rows = []
    for sym, name, group, *rest in ASSETS:
        full = rest[0] if rest else True
        ar = m["avg_return_pct"].get(sym)
        wr = m["win_rate_pct"].get(sym)
        ex = m["excess_vs_spy_pct"].get(sym)
        if ar is None:
            continue
        tag = "" if full else "(短样本)"
        ex_fmt = "{:+}%".format(ex) if ex is not None else "-"
        rows.append("| {} | {}{} | {:+}% | {}% | {} |".format(sym, name, tag, ar, wr, ex_fmt))
    return "\n".join(rows)


def build_report():
    L = []
    a = L.append

    a("# 美股月度宏观经济状态与板块轮动规律报告（{}）\n\n".format(DATE))
    a("> 基于标普500、纳斯达克100、道琼斯、罗素2000、11个行业ETF、20+年国债ETF、10年期国债收益率、\n")
    a("> VIX 恐慌指数的真实历史月度数据,分析每年12个月各自的宏观经济状态、资金行业流动规律、\n")
    a("> 以及历史上每个月最适合买入的板块。\n\n")
    a("> 数据源:Yahoo Finance 复权日线。行业ETF自1999-12起约26.5年样本;房地产(XLRE)自2015、\n")
    a("> 通信(XLC)自2018起样本较短,单独标注。10年期国债收益率 ^TNX 自1998-12起。\n")
    a("> 所有数字可由 `src/monthly_macro_analysis.py` 与 `data/processed/monthly_macro_sector.json` 复现。\n\n")
    a("---\n\n")

    # 一、总体速览
    a("## 一、12个月宏观速览总表\n\n")
    a("| 月份 | SPY平均 | SPY胜率 | VIX均值 | 周期-防御差 | 最佳板块 | 最佳收益 | 最差板块 | 最差收益 | 是否适合投资 |\n")
    a("|---|---|---|---|---|---|---|---|---|---|\n")
    for month in range(1, 13):
        m = data["months"][str(month)]
        _, verdict = macro_portrait(m)
        a("| {} | {:+}% | {}% | {} | {:+}% | {} | {:+}% | {} | {:+}% | {} |\n".format(
            m["month_name"], m["spy_avg_pct"], m["spy_win_pct"], m.get("vix_avg", "-"),
            m.get("cyc_def_gap_pct", 0), m.get("best_sector_name", "-"),
            m.get("best_sector_ret", 0), m.get("worst_sector_name", "-"),
            m.get("worst_sector_ret", 0), verdict.replace("(高胜率正收益)", "").replace("(历史平均亏损)", "").replace("(收益波动大)", "")))
    a("\n")

    # 二、月度详细分析
    a("## 二、逐月详细分析\n\n")
    for month in range(1, 13):
        m = data["months"][str(month)]
        portrait, verdict = macro_portrait(m)
        a("### {}月\n\n".format(month))
        a("**宏观状态**: {}\n\n".format(portrait))
        a("**投资适宜度**: {}\n\n".format(verdict))

        a("**本月核心指标**\n\n")
        a("| 指标 | 数值 |\n|---|---|\n")
        a("| 标普500平均月收益 | {:+}% |\n".format(m["spy_avg_pct"]))
        a("| 标普500正收益年数占比(胜率) | {}% |\n".format(m["spy_win_pct"]))
        a("| VIX 月均(历史分位) | {} ({}%) |\n".format(m.get("vix_avg", "-"), m.get("vix_percentile", "-")))
        a("| 10年期国债收益率月均 | {}% |\n".format(m.get("tnx_avg", "-")))
        a("| 周期股平均 - 防御股平均 | {:+}% |\n".format(m.get("cyc_def_gap_pct", 0)))
        a("| 20+年国债ETF(TLT)平均 | {:+}% |\n".format(m.get("bond_returns_pct", {}).get("TLT", "-")))
        a("| 历史最佳板块 | **{}** ({:+}%) |\n".format(m.get("best_sector_name", "-"), m.get("best_sector_ret", 0)))
        a("| 历史最差板块 | {} ({:+}%) |\n\n".format(m.get("worst_sector_name", "-"), m.get("worst_sector_ret", 0)))

        a("**全板块月度表现(按可用历史)**\n\n")
        a("| 代码 | 板块 | 平均收益 | 胜率 | 超额vs标普 |\n|---|---|---|---|---|\n")
        a(fmt_sector_table(m))
        a("\n\n")

    # 三、资金行业流动规律
    a("## 三、资金行业流动规律总结\n\n")
    a("基于12个月各板块的平均收益与超额收益,资金在全年的行业轮动呈现以下规律(纯数据统计):\n\n")

    # build per-sector best month
    sector_best = {}
    sector_worst = {}
    for sym, name, group, *rest in ASSETS:
        full = rest[0] if rest else True
        if not full:
            continue
        month_rets = []
        for month in range(1, 13):
            m = data["months"][str(month)]
            r = m["avg_return_pct"].get(sym)
            if r is not None:
                month_rets.append((month, r))
        if month_rets:
            month_rets.sort(key=lambda x: x[1], reverse=True)
            sector_best[sym] = (name, month_rets[0])
            sector_worst[sym] = (name, month_rets[-1])

    a("**每个板块历史最佳与最差月份**\n\n")
    a("| 板块 | 历史最佳月份 | 收益 | 历史最差月份 | 收益 |\n|---|---|---|---|---|\n")
    for sym, name, group, *rest in ASSETS:
        full = rest[0] if rest else True
        if not full or sym not in sector_best:
            continue
        bn, bm = sector_best[sym]
        wn, wm = sector_worst[sym]
        a("| {} | {}月 | {:+}% | {}月 | {:+}% |\n".format(name, bm[0], bm[1], wm[0], wm[1]))
    a("\n")

    # 四、最佳月度轮动策略
    a("## 四、全年最佳月度板块轮动策略\n\n")
    a("若严格按「每月买入当月历史最佳板块」的轮动策略(纯回测,不含交易成本),全年节奏如下:\n\n")
    a("| 月份 | 历史最佳板块 | 平均收益 | 标普500对比 |\n|---|---|---|---|\n")
    total = 0
    for month in range(1, 13):
        m = data["months"][str(month)]
        bs = m.get("best_sector_name"); br = m.get("best_sector_ret", 0)
        spy = m["spy_avg_pct"]
        total += br
        a("| {}月 | {} | {:+}% | {:+}%({:+}%) |\n".format(month, bs, br, spy, br - spy))
    a("| **全年合计(平均)** | — | **{:+}%** | — |\n\n".format(round(total, 2)))
    a("> 说明:此为「每月历史平均最佳」的统计描述,非交易策略回测。实盘需考虑板块切换的\n")
    a("> 交易成本、税费、以及「历史最佳板块在未来是否延续」的不确定性。\n\n")

    # 五、关键发现
    a("## 五、关键发现\n\n")
    a("1. **9月是全年唯一平均亏损月**:SPY 历史 9 月平均 {:+}%,胜率仅 {}%,\"Sell in May\" 的终点\n".format(
        data["months"]["9"]["spy_avg_pct"], data["months"]["9"]["spy_win_pct"]))
    a("   往往是 9 月,材料板块 {:+}% 最弱。这与财报空窗期、夏季流动性回落高度吻合。\n\n".format(
        data["months"]["9"]["avg_return_pct"].get("XLB", 0)))
    a("2. **11月是最强月份**:SPY 平均 {:+}%,胜率 {}%,材料 {:+}%、工业 {:+}%、罗素2000 {:+}% 全面爆发,\n".format(
        data["months"]["11"]["spy_avg_pct"], data["months"]["11"]["spy_win_pct"],
        data["months"]["11"]["avg_return_pct"].get("XLB", 0),
        data["months"]["11"]["avg_return_pct"].get("XLI", 0),
        data["months"]["11"]["avg_return_pct"].get("IWM", 0)))
    a("   对应\"圣诞行情\"启动 + 三季度财报落地后的预期重置。\n\n")
    a("3. **能源板块在Q1(1-4月)持续领涨**:1月 {:+}%、2月 {:+}%、4月 {:+}%,反映冬季能源需求 +\n".format(
        data["months"]["1"]["avg_return_pct"].get("XLE", 0),
        data["months"]["2"]["avg_return_pct"].get("XLE", 0),
        data["months"]["4"]["avg_return_pct"].get("XLE", 0)))
    a("   年初 OPEC 产量政策窗口。\n\n")
    a("4. **科技板块5月最强**({:+}%),呼应\"Sell in May and go away\"中科技反例——成长股在财报季后\n".format(
        data["months"]["5"]["avg_return_pct"].get("XLK", 0)))
    a("   5月常有估值修复。\n\n")
    a("5. **公用事业/必需消费在恐慌月(3月、9月)相对抗跌**,是典型的防御避风港。\n\n")
    a("6. **金融板块7月最强**({:+}%),与年中利率决议窗口 + 银行业二季度财报相关。\n\n".format(
        data["months"]["7"]["avg_return_pct"].get("XLF", 0)))

    # 六、数据局限
    a("## 六、数据局限\n\n")
    a("1. **季节性不保证重复**:月度平均是26年的统计中心趋势,任何单一年份都可能偏离(如2020年3月疫情)。\n")
    a("2. **行业ETF的结构变化**:GICS分类在2018年重组(如通信XLC拆分、房地产XLRE独立),早期数据有口径差异。\n")
    a("3. **未含交易成本**:板块月度轮动的换仓成本(申赎费、价差、税)未扣除。\n")
    a("4. **宏观状态为统计推断**:VIX/国债/板块表现是宏观因子的代理变量,非直接的宏观经济数据(如GDP、PMI)。\n")
    a("5. **样本起点的偏差**:1999-12起恰好是互联网泡沫顶部,科技板块的早期极值会拉高部分月份的方差。\n\n")

    a("## 附录\n\n")
    a("- 分析引擎:`src/monthly_macro_analysis.py`\n")
    a("- 月度收益明细:`data/processed/monthly_returns_all_assets.csv`\n")
    a("- 月度宏观摘要:`data/processed/monthly_macro_sector_summary.csv`\n")
    a("- 结构化结果:`data/processed/monthly_macro_sector.json`\n")

    return "".join(L)


def main():
    md = build_report()
    out = DOCS / "{}_美股月度宏观经济与板块轮动规律.md".format(DATE)
    out.write_text(md, encoding="utf-8")
    print("report saved:", out, "|", len(md), "chars")


if __name__ == "__main__":
    main()
