# -*- coding: utf-8 -*-
"""Generate the macro-impact comprehensive report, merged with sector cycle."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
PROC = REPO / "data" / "processed"
DOCS = REPO / "docs" / "research"
DATE = "2026-07-01"

summary = json.loads((PROC / "macro_impact_summary.json").read_text(encoding="utf-8"))
cc = pd.read_csv(PROC / "macro_concurrent_corr.csv")
lc = pd.read_csv(PROC / "macro_lagged_corr_impulse.csv")
r2 = pd.read_csv(PROC / "macro_rolling_r2.csv")

SECTOR_NAMES = {"SPY":"标普500","QQQ":"纳斯达克100","DIA":"道琼斯","IWM":"罗素2000",
 "XLK":"科技","XLV":"医疗","XLF":"金融","XLE":"能源","XLY":"可选消费","XLP":"必需消费",
 "XLI":"工业","XLU":"公用事业","XLB":"材料"}
FACTOR_NAMES = {"FFR_change":"联邦基金利率变动","CPI_YOY_change":"CPI通胀同比变动",
 "UNEMP_change":"失业率变动","NFP_YOY_change":"非农就业同比变动","TNX_change":"10年期国债收益率变动"}


def build_report():
    L = []; a = L.append
    a("# 宏观因素对美股波动影响分析报告（{}）\n\n".format(DATE))
    a("> 本报告量化分析美联储利率、CPI通胀、非农就业、失业率、国债收益率等宏观因素\n")
    a("> 对标普500、纳斯达克100及11个行业ETF波动的影响,包括:**影响是否存在、影响多大、\n")
    a("> 持续多久**,并与前序的月度行业轮动周期结合,给出完整的波动归因结论。\n\n")
    a("> 宏观数据源:Alpha Vantage 官方经济指标 API(CPI 1913起、非农 1939起、失业率 1948起、\n")
    a("> 联邦基金利率 1954起、10年期国债 1962起)。市场数据:Yahoo Finance 复权日线。\n")
    a("> 分析区间:1999-12 至 2026-05(约 319 个月,月度对齐)。所有数字可复现。\n\n")
    a("---\n\n")

    # 一、核心结论速览
    a("## 一、核心结论速览\n\n")
    a("| 维度 | 结论 |\n|---|---|\n")
    a("| 宏观是否影响股市 | **是,但有限**。五大宏观因子合计只能解释月度收益波动的约 **{}%**(滚动R²均值) |\n".format(round(summary["rolling_r2_mean"]*100)))
    a("| 最强单一因子 | **10年期国债收益率(TNX)** 与 **CPI通胀**,对能源/金融板块影响最大 |\n")
    a("| 影响最持久的因子 | **CPI通胀** — 当月小幅正相关,但**第8-9个月压制效应最强** |\n")
    a("| 影响最短暂的因子 | **非农就业** — 当月冲击后3个月内基本消散 |\n")
    a("| 最反直觉的发现 | **降息周期股市反而最差**(-0.47%/月),利率平稳期最佳(+1.25%/月) |\n")
    a("| 行业最敏感板块 | **能源(XLE)** 对几乎所有宏观因子最敏感;**公用事业(XLU)** 与利率负相关 |\n")
    a("| 行业最钝感板块 | **必需消费(XLP)**、**医疗(XLV)** — 防御板块对宏观波动免疫 |\n\n")

    # 二、数据与方法
    a("## 二、数据与方法\n\n")
    a("**宏观因子(月度时序,源自 Alpha Vantage)**:\n\n")
    a("| 因子 | 数据序列 | 起点 | 含义 |\n|---|---|---|---|\n")
    a("| FFR_change | 有效联邦基金利率环比变动 | 1954 | 美联储货币政策方向 |\n")
    a("| CPI_YOY_change | CPI 同比通胀率的变动 | 1913 | 通胀加速度 |\n")
    a("| UNEMP_change | 失业率环比变动 | 1948 | 就业市场恶化/改善 |\n")
    a("| NFP_YOY_change | 非农就业同比增速变动 | 1939 | 劳动力扩张动能 |\n")
    a("| TNX_change | 10年期国债收益率月均变动 | 1962 | 长端利率/市场利率预期 |\n\n")
    a("**市场标的**:SPY/QQQ/DIA/IWM + 11个行业ETF(XLK/XLV/XLF/XLE/XLY/XLP/XLI/XLU/XLB/XLRE/XLC)。\n\n")
    a("**四种量化方法**:\n")
    a("1. **同步相关性**:宏观因子当月变动 vs 当月收益(瞬间冲击)\n")
    a("2. **脉冲响应(滞后相关)**:宏观因子 t 月变动 vs t+k 月收益,揭示**影响持续时间**\n")
    a("3. **regime 条件统计**:加息/降息/平稳三种利率环境下板块表现对比\n")
    a("4. **滚动回归 R²**:五因子模型对SPY月度收益的解释力随时间变化\n\n")

    # 三、同步相关性
    a("## 三、同步相关性(当月冲击)\n\n")
    a("宏观因子**当月变动**与各板块**当月收益**的相关系数(正值=同向,负值=反向,|r|<0.1为弱):\n\n")
    a("| 宏观因子 | " + " | ".join(SECTOR_NAMES[s] for s in ["SPY","QQQ","XLF","XLE","XLK","XLV","XLU","XLP"]) + " |\n")
    a("|" + "---|" * 9 + "\n")
    for _, row in cc.iterrows():
        fac = FACTOR_NAMES.get(row["factor"], row["factor"])
        vals = []
        for s in ["SPY","QQQ","XLF","XLE","XLK","XLV","XLU","XLP"]:
            v = row.get(s, float("nan"))
            vals.append("{:+.3f}".format(v) if pd.notna(v) else "—")
        a("| {} | {} |\n".format(fac, " | ".join(vals)))
    a("\n**解读**:\n")
    a("- **TNX(国债收益率)对能源 +0.217 最强**:利率上行反映经济过热/再通胀,能源(通胀受益)领涨。\n")
    a("- **TNX 对公用事业 -0.075**:公用事业是债券替代品,利率上行打压其估值。\n")
    a("- **失业率变动对能源 +0.185**:看似反常,实因失业率变动方向在周期拐点的噪声(失业率上升常伴随大宗商品价格剧烈波动)。\n")
    a("- **非农同比对能源 -0.137**:就业强劲 → 美元强 → 大宗商品(能源)承压,这是稳定的负相关。\n")
    a("- **医疗/必需消费对所有因子相关性 < 0.1**:防御板块确实是宏观免疫的,这是其配置价值的核心。\n\n")

    # 四、脉冲响应(影响持续时间)
    a("## 四、脉冲响应(影响持续时间)\n\n")
    a("这是回答「**宏观冲击影响持续多久**」的核心图表。下表为各因子 t 月变动与 SPY/QQQ **未来 k 月收益**的相关性。\n")
    a("关注相关性的**符号翻转点**和**衰减速度**。\n\n")

    for fac in ["FFR_change","CPI_YOY_change","TNX_change","UNEMP_change","NFP_YOY_change"]:
        sub = lc[lc["factor"] == fac]
        a("**{}** 与未来收益相关性:\n\n".format(FACTOR_NAMES[fac]))
        a("| 滞后(月) | SPY | QQQ | XLF | XLE | XLU |\n|---|---|---|---|---|---|\n")
        for _, row in sub.iterrows():
            cells = []
            for s in ["SPY","QQQ","XLF","XLE","XLU"]:
                v = row.get(s, float("nan"))
                cells.append("{:+.3f}".format(v) if pd.notna(v) else "—")
            a("| {} | {} |\n".format(int(row["lag_months"]), " | ".join(cells)))
        # interpretation
        spy_vals = sub.set_index("lag_months")["SPY"].dropna()
        if len(spy_vals):
            peak_lag = int(spy_vals.abs().idxmax())
            peak_val = spy_vals.loc[peak_lag]
            sign0 = spy_vals.iloc[0] if 0 in spy_vals.index else 0
            a("\n*解读*:SPY 影响在滞后 {} 月达到峰值({:+.3f});当月影响 {:+.3f}。\n\n".format(peak_lag, peak_val, sign0))

    a("**持续时间总结**:\n\n")
    a("| 因子 | 当月影响 | 峰值滞后 | 持续特征 |\n|---|---|---|---|\n")
    a("| CPI通胀 | +0.083 | **8个月(-0.133)** | 最持久,通胀超预期后持续压制股市近一年 |\n")
    a("| 国债收益率TNX | +0.101 | **4个月(-0.100)** | 当月正(经济向好),4个月后转负(融资成本侵蚀) |\n")
    a("| 联邦基金利率FFR | +0.111 | 全年均匀(0.07-0.13) | 持续背景因素,无明显衰减 |\n")
    a("| 失业率 | +0.081 | 7个月(+0.104) | 噪声大,中期有反复 |\n")
    a("| 非农就业 | -0.018 | **3个月后消散** | 最短暂,属一次性事件冲击 |\n\n")

    # 五、regime 条件
    a("## 五、利率周期下的板块表现(regime 分析)\n\n")
    a("按联邦基金利率月度变动分为三种环境,统计 SPY 在各环境下的表现:\n\n")
    rc = summary["regime_conditional"]
    a("| 利率环境 | SPY平均月收益 | SPY胜率 | 样本月数 |\n|---|---|---|---|\n")
    for regime, d in rc.items():
        spy = d.get("SPY", {})
        a("| {} | {:+}% | {}% | {} |\n".format(regime, spy.get("avg_ret_pct","—"), spy.get("win_pct","—"), spy.get("n","—")))
    a("\n**这是最反直觉的发现**:\n")
    a("- **加息期 SPY 仅 +0.08%/月** — 市场对加息有预期,实际加息落地反而平淡。\n")
    a("- **降息期 SPY -0.47%/月(最差)** — 降息是「经济出问题」的信号,历史降息周期(2001、2007-08、2020)都伴随衰退,股市先跌。\n")
    a("- **利率平稳期 SPY +1.25%/月(最佳,胜率67%)** — 政策确定性高时市场最舒服。\n\n")
    a("**各板块在三种环境下的表现**:\n\n")
    for regime, d in rc.items():
        a("**{}**:\n\n".format(regime))
        a("| 板块 | 平均月收益 | 胜率 | 样本 |\n|---|---|---|---|\n")
        # sort by avg ret
        items = sorted(d.items(), key=lambda kv: kv[1].get("avg_ret_pct", -999), reverse=True)
        for sym, dd in items[:6]:
            a("| {} | {:+}% | {}% | {} |\n".format(SECTOR_NAMES.get(sym, sym), dd.get("avg_ret_pct"), dd.get("win_pct"), dd.get("n")))
        a("\n")

    # 六、滚动R2
    a("## 六、宏观对市场波动的解释力(滚动 R²)\n\n")
    a("用五因子(FFR/CPI/失业率/非农/TNX)线性回归解释 SPY 月度收益,滚动60个月窗口的 R²:\n\n")
    a("| 指标 | 数值 |\n|---|---|\n")
    a("| 滚动R²均值 | **{}%** |\n".format(round(summary["rolling_r2_mean"]*100)))
    a("| 最近窗口R² | {}% |\n".format(round(summary["rolling_r2_recent"]*100) if summary.get("rolling_r2_recent") else "—"))
    a("| 剩余未解释(其他因素) | **{}%** |\n\n".format(round((1-summary["rolling_r2_mean"])*100)))
    a("**解读**:宏观五大因子合计只能解释约 **{}%** 的月度收益波动。其余 **{}%** 来自:\n".format(
        round(summary["rolling_r2_mean"]*100), round((1-summary["rolling_r2_mean"])*100)))
    a("- 企业盈利(财报)、估值变动、行业自身周期、地缘政治、市场情绪、流动性、技术面等。\n")
    a("- 这意味着**单靠宏观做择时是不够的**,宏观是「背景板」而非「主驱动」。\n\n")

    # 七、与行业周期结合
    a("## 七、宏观因素与行业周期的综合判断\n\n")
    a("将本报告的宏观影响与前序「月度行业轮动规律」结合,得到更完整的波动归因:\n\n")
    a("**1. 行业季节性 = 财报周期 + 宏观发布窗口的叠加**\n")
    a("- 9月全年最差(-1.2%):不仅是夏季流动性回落,更是 8月底 Jackson Hole 央行年会后的\n")
    a("  政策预期重置 + Q3财报空窗期。宏观脉冲响应显示 CPI 冲击在第8月压制最强,与年初通胀数据\n")
    a("  传导到秋季股市的时间吻合。\n")
    a("- 11月最强(+2.43%):Q3财报全部落地后,市场重新定价 + 圣诞消费旺季预期。此时\n")
    a("  利率政策通常已确定(12月FOMC前),确定性最高。\n\n")
    a("**2. 板块对宏观的敏感度排序(从高到低)**\n\n")
    a("| 敏感度 | 板块 | 主要宏观驱动 |\n|---|---|---|\n")
    a("| 最高 | 能源(XLE) | TNX +0.217, NFP -0.137 — 利率+美元双重敏感 |\n")
    a("| 高 | 金融(XLF) | FFR +0.168, TNX +0.160 — 直接受利率政策影响 |\n")
    a("| 高 | 公用事业(XLU) | TNX -0.075 — 与利率反向(债券替代品) |\n")
    a("| 中 | 科技(XLK)/罗素2000 | FFR/TNX 中度正相关 — 利率敏感型成长 |\n")
    a("| 低(防御) | 必需消费(XLP)、医疗(XLV) | 所有因子相关性<0.1 — 宏观免疫 |\n\n")
    a("**3. 操作启示**\n")
    a("- **加息/通胀上行期**:超配能源、金融,低配公用事业、长久期成长股。\n")
    a("- **降息/衰退期**(历史表现最差):**减仓避险**,持有现金或必需消费、医疗;不要因「降息利好」就抄底。\n")
    a("- **利率平稳期**(历史最佳):满仓宽基(SPY/QQQ),享受确定性溢价。\n")
    a("- **CPI超预期的后续8个月**:降低仓位,尤其科技成长股。\n\n")

    # 八、完整结论
    a("## 八、完整结论\n\n")
    a("1. **宏观因素确实影响美股,但影响被高估了**。五大因子合计解释力约15%,主驱动仍是\n")
    a("   企业盈利与市场情绪。宏观是「风向」而非「引擎」。\n\n")
    a("2. **影响的大小因板块差异巨大**:能源/金融对利率高度敏感(相关系数0.16-0.22),\n")
    a("   防御板块(必需消费/医疗)几乎免疫。这意味着**同一宏观事件对不同持仓影响天差地别**。\n\n")
    a("3. **影响的持续时间是关键的非线性特征**:\n")
    a("   - CPI通胀冲击的负面效应在 **第8-9个月** 才达到峰值(不是当月!),这是最容易被忽视的滞后。\n")
    a("   - 国债收益率冲击 **第4个月** 转负。利率上行先反映经济向好(当月涨),后侵蚀盈利(滞后跌)。\n")
    a("   - 非农是一次性事件冲击,3个月内消散,不值得据此做长期仓位调整。\n\n")
    a("4. **降息≠利好,这是历史最重要的教训**。降息周期股市平均 -0.47%/月,因为降息\n")
    a("   本身就是经济恶化的确认。真正适合投资的是「利率平稳期」(+1.25%/月)。\n\n")
    a("5. **宏观与行业周期的最佳结合方式**:用宏观判断「是否该在场」(平稳期满仓、\n")
    a("   降息期减仓),用行业轮动判断「买什么」(能源Q1、科技5月、金融7月、材料11月)。\n")
    a("   两者叠加,而非相互替代。\n\n")

    a("## 数据局限\n\n")
    a("1. 相关性≠因果性。宏观因子与股市的同步/滞后相关是统计关联,机制可能通过预期传导。\n")
    a("2. 月度数据掩盖了日内的发布冲击(如CPI公布当天的分钟级波动)。\n")
    a("3. 滚动回归假设因子关系线性且稳定,实际存在结构性变化(如2008后量化宽松扭曲利率信号)。\n")
    a("4. 宏观因子间存在共线性(利率与通胀高度相关),单因子相关系数可能高估或低估真实独立影响。\n")
    a("5. 未区分「预期内」vs「超预期」数据。市场只对意外部分反应,本研究用整体变动近似。\n\n")

    a("## 附录\n\n")
    a("- 宏观抓取:`src/fetch_macro.py`(Alpha Vantage)\n")
    a("- 分析引擎:`src/macro_impact_analysis.py`\n")
    a("- 同步相关:`data/processed/macro_concurrent_corr.csv`\n")
    a("- 脉冲响应:`data/processed/macro_lagged_corr_impulse.csv`\n")
    a("- 滚动R²:`data/processed/macro_rolling_r2.csv`\n")
    a("- 宏观原始数据:`data/macro/*.parquet`\n")

    return "".join(L)


def main():
    md = build_report()
    out = DOCS / "{}_宏观因素对美股波动影响分析.md".format(DATE)
    out.write_text(md, encoding="utf-8")
    print("report saved:", out, "|", len(md), "chars")


if __name__ == "__main__":
    main()
