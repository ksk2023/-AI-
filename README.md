# US Stock Quantitative Trading Research

基于历史回测的美股量化交易研究项目。核心目标:用严谨、可复现的数据,验证美股市场的统计规律,为量化交易系统提供决策依据。

> **核心规则**:所有数据必须真实来自 API,严禁假设、估算或编造。详细见 [CLAUDE.md](CLAUDE.md)。

## 项目背景

逐步搭建一个基于历史回测的量化交易系统。第一步先收集可靠的数据源,第二步对具体假设做统计验证。本仓库目前已完成两个核心研究:

1. **大涨后追高收益研究**(2026-06-30):日涨超 10% 后,各周期继续涨概率。
2. **阴阳平衡假设验证**(2026-06-30):纳斯达克综合指数年内的涨/跌天数是否接近 1:1。

后续每完成一个新研究,会按照命名规范推送到 [GitHub](https://github.com/ksk2023/-AI-)。

## 数据源

| 数据源 | 用途 | 限制 | 验证状态 |
|---|---|---|---|
| **Finnhub** | 行业/市值/IPO 分类,实时报价 | 历史 K 线为付费 | ✅ 完整 40 位 key 验证有效 |
| **Alpha Vantage** | 复权周线(WEEKLY_ADJUSTED),全市场名录 | 每日 25 次调用上限 | ✅ 已验证,2020 年起数据 |
| **Yahoo Finance** | 复权日线(cookie+crumb 绕过限流) | 非官方,但数据准确 | ✅ 已验证 26 年历史 |

价格数据全部使用**复权收盘价**(已处理拆股与分红),避免假信号。

## 已完成研究

### 1. 美股大涨后追高收益研究(2026-06-30)

- 报告: [docs/research/2026-06-30_美股大涨后追高收益研究_日线回测.md](docs/research/2026-06-30_美股大涨后追高收益研究_日线回测.md)
- 数据: 65 个标的,436,993 根日线,1999-2026
- 事件: 1549 次日涨幅 ≥ 10% 的大涨事件
- 分类: 25 个细分行业 + 市值类型 + 16 只 ETF

**核心发现**:**股票日大涨(超 10%)后,第二天继续涨的概率仅 39.4%**。短期(1-2 周)追高全面亏损,中长期(半年+)才有正收益。一年胜率 60.5%,中位数收益 +13.4%。

### 2. 美股阴阳平衡假设验证(2026-06-30)

- 报告: [docs/research/2026-06-30_美股阴阳平衡假设验证_纳斯达克综合指数.md](docs/research/2026-06-30_美股阴阳平衡假设验证_纳斯达克综合指数.md)
- 数据: 纳斯达克综合指数(^IXIC),1971-2026,共 56 年 13,964 个交易日

**核心结论:假设不成立。**累计涨/跌比例约 1.27:1(涨 7,787 / 跌 6,139),50/56 年严重偏离 1:1。仅 2001 年最接近 1:1(50.4% vs 49.6%)。美股作为长期向上的资产,结构是"涨多跌少"而非"涨跌平衡"。

## 目录结构

```
.
├── README.md                           # 本文件
├── CLAUDE.md                           # 长期记忆与核心规则
├── requirements.txt                    # Python 依赖
├── .env.example                        # 环境变量模板(不含真实密钥)
├── .gitignore                          # .env、缓存等永不提交
├── src/                                # 可复现的代码
│   ├── config.py                       # 环境变量加载(.env → 内存)
│   ├── universe.py                     # 股票池定义(53 只 + 16 只 ETF)
│   ├── data_fetch.py                   # Finnhub/AV 数据拉取
│   ├── yahoo_daily.py                  # Yahoo 日线拉取(cookie+crumb)
│   ├── analysis.py                     # 周线大涨事件分析引擎
│   ├── analysis_daily.py               # 日线大涨事件分析引擎
│   ├── yin_yang_analysis.py            # 阴阳平衡逐年分析
│   └── report.py                       # 报告生成器
├── data/
│   ├── raw/                            # 原始数据(parquet)
│   │   ├── daily_AAPL.parquet          # 65 个标的的日线
│   │   ├── daily_NASDAQ_COMPOSITE.parquet  # 纳斯达克综合指数完整历史
│   │   ├── weekly_*.parquet            # 12 只标的的周线
│   │   ├── profiles.parquet            # 53 只个股的行业/市值分类
│   │   └── listing_status.csv          # AV 全市场名录(9596 个标的)
│   └── processed/                      # 处理后的分析结果(CSV/parquet)
│       ├── daily_by_period.csv         # 日线 6 周期统计
│       ├── daily_by_sector.csv         # 日线行业分类
│       ├── daily_by_cap.csv            # 日线市值分类
│       ├── daily_events.parquet        # 1549 次大涨事件明细
│       ├── nasdaq_yin_yang_balance.csv # 56 年逐年涨跌统计
│       └── ...
└── docs/
    └── research/                       # 研究报告(命名:YYYY-MM-DD_主题.md)
        ├── 2026-06-30_美股大涨后追高收益研究_日线回测.md
        └── 2026-06-30_美股阴阳平衡假设验证_纳斯达克综合指数.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

复制 `.env.example` 为 `.env`,填入真实密钥:

```
FINANCE_HUB_API_KEY=你的 Finnhub 完整 40 位 key
ALPHA_VANTAGE_API_KEY=你的 Alpha Vantage key
```

> `.env` 已在 `.gitignore` 中,**绝不会**被提交。

### 3. 拉取数据(可选,数据已落盘)

```bash
# Finnhub 行业分类
python src/data_fetch.py --profiles

# Alpha Vantage 复权周线(每日 25 次上限,需要分多天)
python src/data_fetch.py --weekly

# Yahoo Finance 复权日线
python src/yahoo_daily.py
```

### 4. 跑分析

```bash
# 大涨后追高(日线)
python src/analysis_daily.py

# 大涨后追高(周线,12 只股票)
python src/analysis.py

# 阴阳平衡逐年分析
python src/yin_yang_analysis.py
```

### 5. 生成报告

```bash
python src/report.py
```

## 命名与推送规范

**研究报告命名**:`docs/research/YYYY-MM-DD_研究主题.md`

- 日期精确到日
- 同一主题不覆盖,按日期排序自然形成时间线
- 主题使用中文,简短描述研究内容

**Git 推送流程**:

```bash
git add -A
git status   # 确认 .env 没被暂存
git commit -m "..."
git push origin main
```

每次完成研究都按此流程推送,不会覆盖之前的文件。

## 数据局限与已知偏差

| 局限 | 影响 | 缓解方案 |
|---|---|---|
| **幸存者偏差** | 当前样本仅含现存股票,AV 名录显示约 32% 美股已退市,追高收益可能被系统性高估 | 接入 Polygon 全市场(含退市股)历史 |
| **数据源免费层限制** | Finnhub 无历史 K 线,AV 每日 25 次,DAILY_ADJUSTED 为付费 | 用 Yahoo Finance 日线兜底(已实测可用) |
| **事件定义单一** | 大涨定义为收盘对收盘 ≥10%,未区分财报跳空、行业联动等 | 后续按触发原因细化条件概率 |
| **回测未含交易成本** | 实际收益会低于报告数值 | 后续接入滑点与佣金模型 |

## 后续研究方向

1. 接入 Polygon.io 全市场数据,消除幸存者偏差。
2. 把"大涨"细分到财报跳空 / 行业联动 / 指数成分变动等触发原因,做条件概率分析。
3. 引入更多时间序列因子(成交量、波动率、估值),做多因子回归。
4. 搭建完整的事件驱动回测引擎与组合优化框架。

## 联系方式与许可

仅供个人量化研究使用,不构成任何投资建议。历史收益不代表未来表现。