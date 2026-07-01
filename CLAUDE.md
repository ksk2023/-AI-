# 项目长期记忆 / Long-term Memory

## 核心规则(必须严格遵守)

1. **所有数据必须准确,不能有任何假设推断。** 每一个数字都必须来自真实获取的 API 数据,严禁编造、估算或猜测。如果数据缺失,必须明确标注缺失,而不是用假设值填充。

2. **数据源可追溯。** 每个分析结论必须能追溯到具体的数据文件和获取来源(API + 时间)。

3. **按日期+内容命名研究报告。** 主题报告放入 `docs/research/` 顶层,以 `YYYY-MM-DD_研究主题` 命名;**个股报告放入 `docs/research/个股分析/<TICKER>/`**,以 `YYYY-MM-DD_<TICKER>_历史回测分析.md` 命名。均不覆盖之前的报告。

4. **API 密钥安全。** `.env` 永远不提交到 git,代码通过环境变量读取。

5. **推送规范。** 每次完成研究后 `git add → commit → push` 到 GitHub(origin: git@github.com:ksk2023/-AI-.git, branch: main)。

## 数据源

- Finnhub(完整 40 位 key): 行业分类 profile2(免费)、实时 quote。历史 K 线为付费(403)。
- Alpha Vantage: WEEKLY_ADJUSTED 复权周线(免费,每日限 25 次)。DAILY_ADJUSTED 为付费。
- Yahoo Finance: 复权日线(通过 cookie+crumb 认证绕过限流),含拆股分红复权。非官方但数据准确。

## 已完成研究

主题研究(横向, docs/research/ 顶层):
- 2026-06-30 大涨后追高收益研究: 日大涨(>10%)后第二天继续涨概率 39.4%
- 2026-06-30 美股阴阳平衡假设验证(纳斯达克综合指数): 假设不成立, 涨/跌约 1.27:1
- 2026-06-30 杠杆压力测试与风控回测(NASDAQ)
- 2026-07-01 QQQ 杠杆与回撤爆仓分析: 全期 MDD -82.96%, 临界杠杆 1.21x, 1.5x+ 必爆仓
- 2026-07-01 科技股组合历史回测横向对比(17 家)

个股历史回测(docs/research/个股分析/<TICKER>/):
七姐妹(AAPL/MSFT/NVDA/GOOGL/META/AMZN/TSLA)、美光(MU)、闪迪(SNDK)、SK海力士(000660.KS)、三星(005930.KS)、康宁(GLW)、迈威尔(MRVL)、台积电(TSM+2330.TW)、诺基亚(NOK)、SpaceX(SPCX, IPO 2026-06-12, 仅 12 天样本)。每只含回测 .md 与结构化 _metrics.json。

## 数据质量注意(必须遵守)

- SK海力士(000660.KS)的 Yahoo adj_close 存在负值(复权 bug), 分析时回退为原始 close 并标注。
- 闪迪 SNDK 因 2016 被西部数据收购、2025 重新分拆, 存在 9 年数据断层, 绝不跨实体拼接。
- Yahoo 代码 SND 实为 Smart Sand 而非闪迪, 真正的闪迪为 SNDK(2025 重新上市)。
- SpaceX 代码为 SPCX(2026-06-12 纳斯达克 IPO), 非 SPCE(维珍银河)或 RKLB(Rocket Lab)。
