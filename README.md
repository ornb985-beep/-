# OIC · 商业操盘手

商机分析与操盘系统 v4 —— **确定性内核 + 终局蓝图**。

零第三方依赖，`python3` 直接可跑。

```bash
python -m unittest discover -s tests -v      # 432 项测试
```

**先看这个**：[docs/v4/11-全景总纲.md](docs/v4/11-全景总纲.md) ——
当前系统的完整状态，每条公式、每个拒绝条件、每个实证数字、每个已抓到的错误。

**知识库**：[kb/](kb/README.md) —— 210 条原子条目 + 7 份技能流程，
可追溯、可叠加进化、可复用迭代。校验器强制每条都有真实出处。

```bash
python -m oic.kb --stats            # 全库概况
python -m oic.kb --find 剪刀差       # 搜
python -m oic.kb --show K-STA-024   # 看一条被推翻的结论及其教训
```

---

## 这是什么

一套把商机分析从"更华丽的猜测"变成"可复现、可审计、不自欺"的系统。

四道门定义了它要达到的效果，也定义了什么时候才允许对外宣称：

| 门 | 判据 | 状态 |
|---|---|---|
| **G0 可复现** | `verify_scores` 双跑逐字节一致 | ✅ **已通过** |
| **G1 有区分度** | ≥5 品类间指标不塌缩成同一档 | ⬜ 需真实数据 |
| **G2 比瞎猜强** | `BS < UNC` 且样本 ≥30 | ⬜ 现有 11 条 |
| **G3 比人省** | 系统 top-10 ≥ 人工 top-10 | ⬜ |
| **G4 有时间差** | 比公开榜单提前的中位天数 >0 | ⬜ |

**这套设计能保证「可复现、可审计、不自欺」，不能保证「预测准」。**
准不准要等 G2 跑出来，而那需要真实数据，不需要更多功能。

---

## 已实现

| 模块 | 内容 |
|---|---|
| `oic/scoring/` | 四维评分、供给侧剪刀差、切换势能、Ulwick/Kano、HHI、红线、**logit-pooling 聚合**、**共形预测**、**Kelly 三重安全阀**、`verify_scores` |
| `oic/calibration/` | Brier + **Murphy 三分解**、BSS/RBS、**Beta-Binomial 分层借力**、**代理结局双通道闸门** |
| `oic/compliance/` | **证券边界拦截器**（7/7 拦截，7/7 零误杀）、**AI 双标识**、**数据源白名单** |
| `oic/evidence/` | **span 字符级校验**、时效衰减、双源锚定、**真值发现** |
| `oic/eval/` | span P/R/F1、Cohen's κ、NDCG@k、CI 门禁 |
| `oic/research/` | 指标分类学、单位归一、**as-of 时间闸**、**六项确定性纠错**、双队列回测、八角度深度调查、变化率引擎 |
| `oic/stats/` | **精确置换检验**、Bootstrap CI、运气基线、Benjamini-Hochberg、**PBO** |
| `oic/sources/` | SEC EDGAR / 巨潮索引、招股书解析、**RSS 适配器**、**合规通用 HTTP 取数器** |
| `oic/deliver/` | top3 BP、90 天四阶段（带量化止损）、人/钱/平台 |
| `oic/pipeline/` | 成本硬顶 + 漏斗可行性断言 |
| `oic/sdk.py` | **嵌入你的 App/智能体**——把纪律一起打包，不只是转发 import |
| `oic/kb/` | **知识库内核**——六条校验、确定性索引、supersede/falsify 演化（**无 delete**） |
| `db/schema.sql` | 12 张表 + 不可变触发器 + RLS |

### 三条设计纪律，写进了代码

**① 确定性计算与 LLM 物理隔离**

`oic/scoring/` 零网络、零时钟、零随机。一条 AST 静态检查测试确保它不会
`import random/time/datetime`。`verify_scores` 双跑比对，
并有**反向测试**证明这个断言真的会失败。

**② 样本不足时拒绝输出，而不是给默认值**

```python
position_size(wins=5, trials=10, payoff_b=3.0, available_budget=100_000)
# → refused=True, "拒绝输出仓位：已解析结局 10 条 < 所需 30 条"
```

Kelly 对胜率高估极度敏感 —— 真实 20% 误估为 40% 会让长期增长率变负。
在 Outcome 表为空的现在，这个函数永远拒绝。**这是正确行为，不是缺陷。**

**③ 数值幻觉在字符级被拦掉**

```python
verify_claim(claim, raw_text)   # 声称的数字必须真在原文 span 里
# 原文"2.8万" 不能匹配声称的 "3万" —— 容差不覆盖四舍五入
```

---

## 快速上手

```python
from oic.scoring.engine import OpportunityInput, verify_scores
from oic.scoring.dimensions import GradedText

result = verify_scores(OpportunityInput(
    opportunity_id="OPP-001", title="露营便携咖啡器具",
    c=82, o=70, d=88, e=75,
    capital_rmb=300_000, team_descriptions=("全栈开发", "增长运营"),
    demand_growth_pct=45, supply_growth_pct=12,
    deregistered_12m=40, active_companies=800, competitor_count=35,
    push=72, pull=68, anxiety=30, inertia=25,
    importance=9, satisfaction=4,
    market_shares_pct=(18, 12, 9, 7, 5, 4, 3),
    evidence=(GradedText("该类目月销破万单", "A"),),
    fake_review_score=15, category="户外露营",
))

for line in result.audit:
    print(line)
```

每个分数都展开成一行可复算算式：

```
需求强度 = 82×0.5 + 88×0.5 = 85.00
可行性 = 70×0.4 + 75×0.4 + 68.3×0.2 = 71.66
总分 = 85.00×0.5 + 71.66×0.5 = 78.33
变现系数 1.2 —— A/B 级来源出现成交证据词: 月销、万单
剪刀差 M = 45% − 12% = 33%
成熟度 L2（同类企业 35 家）→ 文案策略：把效果说得更极致
切换势能 = (72 + 68) − (30 + 25) = 85
排序分 = 78.33 × 1.2 × 1.3 × 0.9500 × 0.8500 × 1(红线) = 98.6723
⚠️ 以下参数未经真实数据校准，仅为先验值：供给侧参数(k/M分档)、红线阈值…
```

---

## 自检

```bash
python -m unittest discover -s tests -v                # 全量测试
python -m oic.scoring.kelly --selftest                 # Kelly 三重安全阀
python -m oic.calibration.report --selftest            # Brier/Murphy/分层/代理
python -m oic.compliance.securities_guard --selftest   # 100% 拦截 / 0 误杀
python -m oic.evidence.grounding --selftest            # span 字符级校验
python -m oic.research.audit --selftest                # 纠错内核（含 100× 单位错回归）
python -m oic.stats.overfit --selftest                 # 20 特征 × n=8 必须报高 PBO
python -m oic.kb --check                               # 知识库六条校验
python -m oic.kb --selftest                            # 断言六道闸真的会拦
python -m oic.eval.run --golden data/golden.seed.jsonl --gate
```

---

## 文档

| | |
|---|---|
| [00 总纲与终局判据](docs/v4/00-总纲与终局判据.md) | G0–G4 四道门 + 三条铁律 |
| [01 功能全集](docs/v4/01-功能全集.md) | F0.1–F9.4 逐条状态 |
| [02 公式与算法规范](docs/v4/02-公式与算法规范.md) | 全部数学契约 |
| [03 数据契约与 Schema](docs/v4/03-数据契约与Schema.md) | 12 张表及每条约束的理由 |
| [04 Agent 契约](docs/v4/04-Agent契约.md) | 输入/输出/done/迭代上限 |
| [05 Eval 与门禁](docs/v4/05-Eval与门禁.md) | 三级指标 + CI |
| [06 合规内核](docs/v4/06-合规内核.md) | 证券边界 / AI 标识 / PIPL |
| [07 路线图与失效模式](docs/v4/07-路线图与回退规则.md) | Wave 0–5 + **10 条已知失效模式** |
| [08 操盘手全流程](docs/v4/08-操盘手全流程.md) | 三段式框架落地 |
| [09 方案融合与缺口](docs/v4/09-方案融合与缺口.md) | 与 Kimi 设计稿的合并结论 |
| [10 嵌入你的App](docs/v4/10-嵌入你的App.md) | SDK 接入 + 为何没做默认全网爬虫 |
| **[11 全景总纲](docs/v4/11-全景总纲.md)** | **后端全量：公式/拒绝条件/实证数字/错误清单** |
| [12 无限检索与智能体集群](docs/v4/12-无限检索与智能体集群.md) | 不限成本决策 / 分层降本 / 多方求证 / 「躺赚」口径 |
| **[知识库](kb/README.md)** | **210 条条目 + 7 份技能流程 + 分类学 + 字段契约** |

---

## 当前的三个阻塞点（都不是工程问题）

| 阻塞 | 影响 | 解法 |
|---|---|---|
| **供给侧数据不可得**（覆盖 5/30，扩样本没变） | 剪刀差是最大差异化，现在悬空 | 企查查开放平台报价，或在有网机器上跑招股书管线 |
| **法务未放行任何数据源** | L1 采集层 | 把 `source_registry` 送法务，逐个 `clear_source()` |
| **已解析结局 11 < 30** | Kelly / 概率 / G2 全部拒绝输出 | 扩样本到 40+ |
| **单 agent 基线未测量** | 铁律 2 禁止扩多智能体 | 测一次 |

供给侧那条**决定产品形态，不是技术问题**。

不要在这几条之前继续加功能。现在缺的不是算法，是事实。

---

> ⚠️ 本仓库的合规内容为工程化的研究性梳理，不构成法律意见。
> 落地前须请中国执业律师就具体功能做合规审查。
