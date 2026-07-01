# US Stock Quantitative Trading Research

基于历史回测的美股量化交易研究项目。核心目标:用严谨、可复现的数据,验证美股市场的统计规律,为量化交易系统提供决策依据。

> **核心规则**:所有数据必须真实来自 API,严禁假设、估算或编造。详细见 [CLAUDE.md](CLAUDE.md)。

## 项目背景

逐步搭建一个基于历史回测的量化交易系统。第一步收集可靠的数据源,第二步对具体假设做统计验证,第三步对个股做系统性历史回测。所有研究按日期+主题命名,推送至 [GitHub](https://github.com/ksk2023/-AI-),不覆盖历史报告。

## 数据源

| 数据源 | 用途 | 限制 | 验证状态 |
|---|---|---|---|
| **Yahoo Finance** | 复权日线(美股/韩股/台股/ADR),个股与指数 | 非官方接口,但数据准确 | ✅ 主力数据源,覆盖 1998-2026 |
| **Finnhub** | 行业/市值/IPO 分类,实时报价 | 历史 K 线为付费 | ✅ 完整 40 位 key 验证有效 |
| **Alpha Vantage** | 复权周线(WEEKLY_ADJUSTED),全市场名录 | 每日 25 次调用上限 | ✅ 已验证 |

价格数据全部使用**复权收盘价**(已处理拆股与分红),避免假信号。

> 已知数据质量坑(均已处理):SK海力士的 Yahoo adj_close 出现负值(复权算法 bug),已回退为原始 close;闪迪 SNDK 因 2016 被收购、2025 重新分拆存在 9 年数据断层,仅分析 2025 后;`SND` 实为 Smart Sand 而非闪迪,已剔除。

## 已完成研究

### 横向主题研究

| # | 主题 | 日期 | 报告 |
|---|---|---|---|
| 1 | 大涨后追高收益研究(日线回测) | 2026-06-30 | [报告](docs/research/2026-06-30_美股大涨后追高收益研究_日线回测.md) |
| 2 | 美股阴阳平衡假设验证(纳斯达克综合指数) | 2026-06-30 | [报告](docs/research/2026-06-30_美股阴阳平衡假设验证_纳斯达克综合指数.md) |
| 3 | 杠杆压力测试与风控回测(NASDAQ) | 2026-06-30 | [报告](docs/research/2026-06-30_杠杆压力测试与风控回测_NASDAQ.md) |
| 4 | QQQ 杠杆与回撤爆仓分析(27年真实日线) | 2026-07-01 | [报告](docs/research/2026-07-01_QQQ杠杆与回撤爆仓分析.md) |
| 5 | 科技股组合历史回测横向对比(17家) | 2026-07-01 | [报告](docs/research/2026-07-01_科技股组合历史回测横向对比.md) |

**核心发现摘要**:

- **追高**:股票日大涨(超 10%)后第二天继续涨概率仅 39.4%;短期(1-2 周)追高全面亏损,一年胜率 60.5%。
- **阴阳平衡**:假设不成立。纳斯达克累计涨/跌约 1.27:1,美股结构是"涨多跌少"而非"涨跌平衡"。
- **QQQ 杠杆**:全期 MDD -82.96%,恢复用 16.5 年;1.5x 以上任何维持保证金在真实历史中必爆仓;理论临界杠杆 1.21x。
- **科技股共性**:高 CAGR 必然伴随 40%+ 波动率;存储半导体(美光/康宁/海力士)是"周期地狱",回撤深至 -98%;稳定赢家涨天占比 52-53%。

### 个股历史回测(17 家)

每家独立文件夹,位于 [docs/research/个股分析/](docs/research/个股分析/):

| 板块 | 公司 | 代码 | 文件夹 |
|---|---|---|---|
| 美股七姐妹 | 苹果 / 微软 / 英伟达 / 谷歌 / Meta / 亚马逊 / 特斯拉 | AAPL MSFT NVDA GOOGL META AMZN TSLA | [个股分析/](docs/research/个股分析/) |
| 存储半导体 | 美光 / 闪迪 / SK海力士 / 三星电子 | MU SNDK 000660.KS 005930.KS | 同上 |
| 晶圆代工 | 台积电(ADR + 台湾本股) | TSM 2330.TW | 同上 |
| 通信/网络 | 诺基亚 / 迈威尔 / 康宁 | NOK MRVL GLW | 同上 |
| 航天 | SpaceX | SPCX | [SPCX/](docs/research/个股分析/SPCX/) |

每份个股报告包含:总收益/CAGR/波动率/夏普/Sortino、最大回撤及恢复时长、阴阳平衡(涨跌天数)、月度季节性、逐年收益、滚动252日窗口、与 SPY/QQQ/纳指相关性、杠杆爆仓敏感度。结构化指标同步保存为 `_metrics.json`。

> **SpaceX 说明**:`SPCX` 于 2026-06-12 在纳斯达克 IPO,截至回测仅 12 个交易日,长期指标无统计意义,仅作 IPO 初期观察。详见 [SPCX IPO 与数据局限说明](docs/research/个股分析/SPCX/2026-07-01_SPCX_IPO与数据局限说明.md)。

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
│   ├── universe.py                     # 基础股票池定义
│   ├── data_fetch.py                   # Finnhub/AV 数据拉取
│   ├── yahoo_daily.py                  # Yahoo 日线拉取(cookie+crumb 认证)
│   ├── fetch_tech_batch.py             # 科技股批量抓取(含韩股/台股)
│   ├── analysis.py / analysis_daily.py # 大涨事件分析引擎(周/日线)
│   ├── yin_yang_analysis.py            # 阴阳平衡逐年分析
│   ├── leverage_stress.py              # NASDAQ 杠杆压力测试
│   ├── qqq_leverage_stress.py          # QQQ 杠杆与爆仓分析
│   ├── stock_analysis.py               # 通用单股回测分析引擎
│   ├── gen_tech_reports.py             # 个股报告生成器
│   ├── gen_comparison_report.py        # 科技股横向对比报告生成器
│   └── report.py                       # 早期报告生成器
├── data/
│   ├── raw/                            # 原始数据(parquet)
│   │   ├── daily_*.parquet             # 各标的日线(美股/韩股/台股/指数/ETF)
│   │   └── ...
│   └── processed/                      # 处理后的分析结果(CSV/parquet/json)
└── docs/
    └── research/                       # 研究报告
        ├── 2026-06-30_*.md             # 主题报告(按日期+主题命名)
        ├── 2026-07-01_*.md
        └── 个股分析/                   # 个股回测(每股一文件夹)
            ├── AAPL/
            │   ├── 2026-07-01_AAPL_历史回测分析.md
            │   └── 2026-07-01_AAPL_metrics.json
            ├── NVDA/  TSLA/  ...        # 其余个股同构
            └── SPCX/                   # SpaceX(含 IPO 数据局限说明)
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

### 3. 拉取数据

```bash
# 科技股批量日线(美股/韩股/台股,含七姐妹、存储、代工、SpaceX)
python src/fetch_tech_batch.py

# 基础股票池日线
python src/yahoo_daily.py

# Finnhub 行业分类 / AV 复权周线
python src/data_fetch.py --profiles
python src/data_fetch.py --weekly
```

### 4. 跑分析与生成报告

```bash
# 个股回测(17 家,输出到 docs/research/个股分析/<TICKER>/)
python src/gen_tech_reports.py

# 科技股横向对比
python src/gen_comparison_report.py

# 早期研究:大涨追高 / 阴阳平衡 / NASDAQ杠杆
python src/analysis_daily.py
python src/yin_yang_analysis.py
python src/qqq_leverage_stress.py
```

## 命名与推送规范

**研究报告命名**:`docs/research/YYYY-MM-DD_研究主题.md`(主题报告)或 `docs/research/个股分析/<TICKER>/YYYY-MM-DD_<TICKER>_历史回测分析.md`(个股报告)。

- 日期精确到日,同一主题不覆盖,按日期自然形成时间线
- 个股报告每股一文件夹,新增股票只需在 `src/gen_tech_reports.py` 的 `STOCKS` 列表追加一行
- 主题使用中文,简短描述研究内容

**Git 推送流程**:

```bash
git add -A
git status   # 确认 .env 没被暂存
git commit -m "..."
git push origin main
```

## 数据局限与已知偏差

| 局限 | 影响 | 缓解方案 |
|---|---|---|
| **幸存者偏差** | 样本仅含现存股票,追高收益可能被系统性高估 | 接入 Polygon 全市场(含退市股)历史 |
| **数据断层** | 闪迪 2016-2025 被收购期间无独立行情;SpaceX 仅 12 天 | 如实标注,不做跨实体拼接或外推 |
| **Yahoo 韩股复权 bug** | SK海力士 adj_close 出现负值 | 已回退为原始 close 并标注 |
| **回测未含交易成本** | 实际收益会低于报告数值 | 后续接入滑点与佣金模型 |
| **单一数据源** | 全部依赖 Yahoo 非官方接口 | 关键结论交叉验证多源 |

## 新增个股分析

如需分析新股票:

1. 在 `src/fetch_tech_batch.py` 的 `TARGETS` 列表追加 `(代码, 中文名, 市场)`,运行抓取。
2. 在 `src/gen_tech_reports.py` 的 `STOCKS` 列表追加 `(代码, 中文名, 市场, 行业)`,运行生成。
3. 运行 `src/gen_comparison_report.py` 更新横向对比。
4. 报告自动写入 `docs/research/个股分析/<代码>/`,不覆盖历史。

## 联系方式与许可

仅供个人量化研究使用,不构成任何投资建议。历史收益不代表未来表现。
