# -*- coding: utf-8 -*-
"""Generate the cross-stock comparison report from per-ticker metrics.json files."""
from __future__ import annotations

import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESEARCH = REPO / "docs" / "research"
STOCK_DIR = RESEARCH / "个股分析"
DATE = "2026-07-01"

# load all per-ticker metrics from the 个股分析 subfolder
records = []
for f in sorted(glob.glob(str(STOCK_DIR / "*" / "{}_*_metrics.json".format(DATE)))):
    r = json.loads(Path(f).read_text(encoding="utf-8"))
    records.append(r)


def fmt(x, suffix="", width=8):
    if x is None:
        return "—"
    if isinstance(x, float) and (x != x):  # nan
        return "—"
    s = ("{:" + ".2f".format() + "}{}").format(x, suffix)
    return s


def main():
    L = []
    a = L.append

    a("# 科技股组合历史回测横向对比报告（{}）\n\n".format(DATE))
    a("> 本报告汇总 16 家科技/半导体公司的历史回测指标，数据均来自 Yahoo Finance 复权日线，\n")
    a("> 可由各 `docs/research/<TICKER>/<DATE>_<TICKER>_metrics.json` 与 `src/stock_analysis.py` 复现。\n")
    a("> SpaceX（SPCX）于 2026-06-12 IPO，样本仅 12 个交易日，单独列入「样本不足」组，不参与长期排名。\n\n")
    a("---\n\n")

    # ---- Section 1: master comparison table ----
    a("## 一、核心指标横向对比\n\n")
    a("按 **年化收益 CAGR 降序** 排列（SNDK 因样本仅 1.4 年单独标注，不参与长期排名）：\n\n")
    a("| 证券 | 名称 | 市场 | 样本年数 | 累计收益 | **CAGR** | 年化波动 | 夏普 | 最大回撤 | 涨天占比 |\n")
    a("|---|---|---|---|---|---|---|---|---|---|\n")

    long_term = [r for r in records if r["span_years"] >= 5]
    short_term = [r for r in records if r["span_years"] < 5]
    long_term.sort(key=lambda r: (r["cagr_pct"] if r["cagr_pct"] == r["cagr_pct"] else -999), reverse=True)

    for r in long_term:
        mdd = r["max_drawdown"]["mdd_pct"]
        a("| {} | {} | {} | {} | {:+}% | **{:+}%** | {}% | {} | {}% | {}% |\n".format(
            r["symbol"], r["display_name"], r["market"], r["span_years"],
            r["total_return_pct"], r["cagr_pct"], r["annualized_vol_pct"],
            r["sharpe"], mdd, r["win_loss"]["up_ratio_pct"]))

    a("\n**样本不足 5 年（单独列出，统计意义有限）：**\n\n")
    for r in short_term:
        mdd = r["max_drawdown"]["mdd_pct"]
        a("| {} | {} | {} | {} | {:+}% | **{:+}%** | {}% | {} | {}% | {}% |\n".format(
            r["symbol"], r["display_name"], r["market"], r["span_years"],
            r["total_return_pct"], r["cagr_pct"], r["annualized_vol_pct"],
            r["sharpe"], mdd, r["win_loss"]["up_ratio_pct"]))
    a("\n")

    # ---- Section 2: return leaders ----
    a("## 二、收益排行（长期标的，≥5年）\n\n")
    by_cagr = sorted(long_term, key=lambda r: r["cagr_pct"], reverse=True)
    a("| 排名 | 证券 | CAGR | 累计收益 | 年化波动 |\n|---|---|---|---|---|\n")
    for i, r in enumerate(by_cagr, 1):
        a("| {} | {} | **{:+}%** | {:+}% | {}% |\n".format(i, r["display_name"], r["cagr_pct"], r["total_return_pct"], r["annualized_vol_pct"]))
    a("\n")
    a("**观察**：CAGR 前三名 ({}/{}/{}) 全部为高成长科技股，但年化波动普遍 40-60%。\n".format(
        by_cagr[0]["display_name"], by_cagr[1]["display_name"], by_cagr[2]["display_name"]))
    a("高收益伴随高波动是这一板块的铁律，不存在「低波动+高CAGR」的免费午餐。\n\n")

    # ---- Section 3: risk-adjusted (sharpe) ----
    a("## 三、风险调整后收益（夏普比率排行）\n\n")
    a("夏普比率 = (CAGR - 2%) / 年化波动率，衡量每单位风险的超额回报：\n\n")
    by_sharpe = sorted(long_term, key=lambda r: r["sharpe"], reverse=True)
    a("| 排名 | 证券 | 夏普 | CAGR | 年化波动 | 最大回撤 |\n|---|---|---|---|---|---|\n")
    for i, r in enumerate(by_sharpe, 1):
        a("| {} | {} | **{}** | {:+}% | {}% | {}% |\n".format(
            i, r["display_name"], r["sharpe"], r["cagr_pct"], r["annualized_vol_pct"], r["max_drawdown"]["mdd_pct"]))
    a("\n")
    a("**观察**：夏普排名前列的标的波动率显著低于 CAGR 榜首，说明「活得久」比「跑得快」更提升风险调整收益。\n")
    a("诺基亚夏普接近 0，印证了「价值陷阱」——低波动但更低收益。\n\n")

    # ---- Section 4: drawdown resilience ----
    a("## 四、回撤韧性（最大回撤从浅到深）\n\n")
    by_mdd = sorted(long_term, key=lambda r: r["max_drawdown"]["mdd_pct"], reverse=True)
    a("| 排名 | 证券 | 最大回撤 | 谷底日期 | 是否恢复 | 恢复天数 |\n|---|---|---|---|---|---|\n")
    for i, r in enumerate(by_mdd, 1):
        m = r["max_drawdown"]
        rec = "✅ 已恢复" if m["recovered"] else "❌ 未恢复"
        days = m["recovery_days"] if m["recovery_days"] is not None else "—"
        a("| {} | {} | {}% | {} | {} | {} |\n".format(i, r["display_name"], m["mdd_pct"], m["trough_date"], rec, days))
    a("\n")
    a("**观察**：康宁、美光回撤接近 -99%，意味着历史峰值买入几乎归零；\n")
    a("谷歌、微软回撤相对温和（-65% ~ -69%），是科技股中韧性最强的。\n")
    a("半导体存储周期股（美光、海力士、康宁）系统性呈现「极端深回撤 + 长恢复期」特征。\n\n")

    # ---- Section 5: leverage critical thresholds ----
    a("## 五、杠杆爆仓临界（基于各股历史最坏回撤）\n\n")
    a("临界杠杆 = 1 / |最大回撤|。超过此值在该股历史最坏情境下清盘：\n\n")
    a("| 证券 | 最大回撤 | **临界杠杆** | 2x 命运 | 3x 命运 |\n|---|---|---|---|---|\n")
    for r in records:
        mdd = r["max_drawdown"]["mdd_pct"]
        if mdd == 0:
            continue
        lev = r["leverage_sensitivity"]
        cl = lev.get("critical_leverage", "—")
        l2 = lev.get("2.0") or lev.get(2.0) or {}
        l3 = lev.get("3.0") or lev.get(3.0) or {}
        f2 = "✅ 活" if l2.get("survives") else "❌ 爆"
        f3 = "✅ 活" if l3.get("survives") else "❌ 爆"
        a("| {} | {}% | **{}x** | {} | {} |\n".format(r["display_name"], mdd, cl, f2, f3))
    a("\n")
    a("**观察**：除少数回撤浅的标的外，**2x 杠杆在大多数科技股的历史最坏情境下都会爆仓**。\n")
    a("存储/材料周期股（康宁-99%、美光-98%）的临界杠杆甚至低于 1.02x，意味着连满仓都不安全。\n\n")

    # ---- Section 6: yin-yang balance ----
    a("## 六、阴阳平衡（涨跌天数）\n\n")
    a("| 证券 | 上涨天数 | 下跌天数 | **涨天占比** | 单日最大涨 | 单日最大跌 |\n|---|---|---|---|---|---|\n")
    for r in records:
        wl = r["win_loss"]
        a("| {} | {:,} | {:,} | **{}%** | {:+}% | {:+}% |\n".format(
            r["display_name"], wl["up_days"], wl["down_days"], wl["up_ratio_pct"],
            wl["best_day_pct"], wl["worst_day_pct"]))
    a("\n")
    a("**观察**：长期赢家（苹果、谷歌、Meta）的涨天占比稳定在 **52-53%**，略高于 50%。\n")
    a("这是「涨多跌少但涨幅大、跌幅小」的长期复利特征，而非阴阳 1:1。\n")
    a("真正接近 1:1 的是诺基亚（49.2%）——长期不涨的股票才符合纯随机游走的阴阳平衡。\n\n")

    # ---- Section 7: correlation cluster ----
    a("## 七、与大盘相关性聚类\n\n")
    a("| 证券 | 与SPY相关 | Beta(SPY) | 与QQQ相关 | Beta(QQQ) |\n|---|---|---|---|---|\n")
    for r in records:
        c = r["correlation"]
        spy = c.get("SPY") or {}
        qqq = c.get("QQQ") or {}
        sc = spy.get("corr", "—") if spy else "—"
        sb = spy.get("beta", "—") if spy else "—"
        qc = qqq.get("corr", "—") if qqq else "—"
        qb = qqq.get("beta", "—") if qqq else "—"
        a("| {} | {} | {} | {} | {} |\n".format(r["display_name"], sc, sb, qc, qb))
    a("\n")
    a("**观察**：美股科技七姐妹与 QQQ 高度相关（普遍 >0.7），是系统性风险的主要载体。\n")
    a("韩股/台股与美股大盘相关性较低（汇率+独立周期），是分散地域风险的候选。\n\n")

    # ---- Section 8: key insights ----
    a("## 八、投资规律总结（基于纯数据统计）\n\n")
    a("1. **高CAGR必然伴随高波动**：CAGR 前 5 名的年化波动无一低于 40%，夏普普遍 0.4-0.7。\n")
    a("   追求翻倍股的代价是承受 60%+ 的年化波动与 70-90% 的最大回撤。\n\n")
    a("2. **存储半导体是「周期地狱」**：美光、康宁、海力士的最大回撤均在 -84% ~ -99%，\n")
    a("   临界杠杆接近 1.0x。这类股票「追高+杠杆」是历史验证的必死组合。\n\n")
    a("3. **长期复利的真相是「涨天略多于跌天」**：稳定赢家涨天占比 52-53%，\n")
    a("   不是靠阴阳1:1，而是靠「涨的幅度大于跌的幅度」。诺基亚式 49% 涨天对应的是零收益。\n\n")
    a("4. **回撤恢复时间是隐形成本**：康宁、诺基亚部分时段至今未恢复或恢复超 10 年，\n")
    a("   即使最终回本，损失的复利时间机会成本无法补偿。\n\n")
    a("5. **地域分散有效**：韩股、台股与美股大盘相关性低于美股内部，\n")
    a("   组合中加入三星、台积电、海力士可降低组合的单一市场风险。\n\n")
    a("6. **杠杆无安全区**：除谷歌、微软等少数浅回撤标的，2x 杠杆在多数科技股历史最坏情境下爆仓。\n")
    a("   杠杆只适合配合严格的波动率防御性减仓机制（详见 QQQ 杠杆报告）。\n\n")

    a("## 九、数据完整性声明\n\n")
    a("- 所有价格数据来自 Yahoo Finance 复权收盘价（自动拆股+分红调整）。\n")
    a("- 韩国股票（SK海力士）的 Yahoo adj_close 存在负值（已知Yahoo bug），已回退为原始 close 序列并标注。\n")
    a("- 闪迪（SNDK）因 2016 被西部数据收购、2025 重新分拆，数据存在 9 年断层，仅分析 2025-02 至今。\n")
    a("- 诺基亚 ADR 价格反映美股交易，与赫尔辛基本股可能有汇率差异。\n")
    a("- SpaceX（SPCX）2026-06-12 IPO，样本仅 12 个交易日，长期指标（CAGR/夏普/季节性）无统计意义，仅作 IPO 初期观察。\n\n")

    a("## 附录：可复现性\n\n")
    a("- 逐股报告：`docs/research/<TICKER>/<DATE>_<TICKER>_历史回测分析.md`\n")
    a("- 结构化指标：`docs/research/<TICKER>/<DATE>_<TICKER>_metrics.json`\n")
    a("- 分析脚本：`src/stock_analysis.py`\n")
    a("- 本汇总生成器：`src/gen_comparison_report.py`\n")

    out = RESEARCH / "{}_科技股组合历史回测横向对比.md".format(DATE)
    out.write_text("".join(L), encoding="utf-8")
    print("comparison report saved:", out, "|", len("".join(L)), "chars")


if __name__ == "__main__":
    main()
