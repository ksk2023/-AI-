# 项目长期记忆 / Long-term Memory

## 核心规则(必须严格遵守)

1. **所有数据必须准确,不能有任何假设推断。** 每一个数字都必须来自真实获取的 API 数据,严禁编造、估算或猜测。如果数据缺失,必须明确标注缺失,而不是用假设值填充。

2. **数据源可追溯。** 每个分析结论必须能追溯到具体的数据文件和获取来源(API + 时间)。

3. **按日期+内容命名研究报告。** 每次新研究的报告放入 `docs/research/` 并以 `YYYY-MM-DD_研究主题` 命名,不覆盖之前的报告。

4. **API 密钥安全。** `.env` 永远不提交到 git,代码通过环境变量读取。

5. **推送规范。** 每次完成研究后 `git add → commit → push` 到 GitHub(origin: git@github.com:ksk2023/-AI-.git, branch: main)。

## 数据源

- Finnhub(完整 40 位 key): 行业分类 profile2(免费)、实时 quote。历史 K 线为付费(403)。
- Alpha Vantage: WEEKLY_ADJUSTED 复权周线(免费,每日限 25 次)。DAILY_ADJUSTED 为付费。
- Yahoo Finance: 复权日线(通过 cookie+crumb 认证绕过限流),含拆股分红复权。非官方但数据准确。

## 已完成研究

- 2026-06-30 大涨后追高收益研究: 日大涨(>10%)后第二天继续涨概率 39.4%