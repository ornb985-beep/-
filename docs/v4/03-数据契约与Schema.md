# 03 · 数据契约与 Schema

实现：[`db/schema.sql`](../../db/schema.sql)（PostgreSQL 15+ / Supabase）

设计原则：**能用数据库约束表达的纪律，就不要只写在文档里。**
一条写在文档里的约束，在赶进度时会被绕过；一条写在 `CHECK` 里的不会。

---

## 一、表清单

| 表 | 作用 | 关键不变式 |
|---|---|---|
| `source_registry` | 数据源白名单 | 爬取源永不可 `cleared`；敏感 PI 未做 PIPIA 不可 `cleared` |
| `opportunity` | 定义验证对象 | RLS 多租户隔离 |
| `evidence` | 结论可追溯 | **数值证据必须 `grounded=true`** |
| `hypothesis` | 防自嗨 | **`falsifiable_when` 非空**——不可证伪的假设不许入库 |
| `experiment` | 真实结果替代猜测 | **`stop_loss` 非空** |
| `decision` | 行动结论 | 冻结决策时刻的 `rank_score` 与 `engine_version` |
| `outcome` | **校准的唯一来源** | `succeeded` 可为 NULL（未解析就是未解析，不插补） |
| `forecast` | 预测存档 | **触发器禁止事后修改预测** |
| `portfolio_position` | 组合与仓位 | **`kelly_fraction ≤ 0.25`** |
| `weight_correction` | 权重学习 | **晋升必须有 Outcome 背书** |
| `passive_signal` | 被动信号回流 | — |
| `audit_log` | 审计 | **触发器禁止 UPDATE/DELETE** |

---

## 二、六张决策表的逻辑

这六张表（Opportunity / Evidence / Hypothesis / Experiment / Decision / Outcome）
构成一个闭环。缺任何一张，闭环就断：

```
Opportunity  定义要验证什么
    ↓
Evidence     凭什么这么说（可追溯到原文字符）
    ↓
Hypothesis   什么观测会证伪它（防自嗨）
    ↓
Experiment   花多少钱、多久、什么算成功、什么时候止损
    ↓
Decision     推进 / 观察 / 补证据 / 转向 / 停止
    ↓
Outcome      真实发生了什么  ←── 这一环断了，上面五环全是自娱自乐
    ↓
（回流到权重学习与校准）
```

### Outcome 是系统命门

```sql
COMMENT ON TABLE outcome IS
    'Outcome 表是整个系统的命门。没有它，权重学习空转，
     系统只学到用户偏好，学不到市场真相。今天不开始记，永远补不回来。';
```

**当前状态：0 条。** 这是整个项目唯一的硬阻塞，写代码解决不了。

---

## 三、关键约束及其理由

### 3.1 数值证据必须经过 grounding

```sql
CONSTRAINT numeric_evidence_must_be_grounded
    CHECK (value_num IS NULL OR grounded = true)
```

未通过 span 字符级校验的数值**在数据库层就进不来**。
配合 `oic/evidence/grounding.py`，形成两道防线。

### 3.2 预测不可修改

```sql
CREATE TRIGGER forecast_no_rewrite BEFORE UPDATE ON forecast ...
    RAISE EXCEPTION '预测存档不可修改 —— 事后改预测等于自欺，校准将失去意义';
```

只允许回填 `actual_outcome` 与 `resolved_at`。
改 `p50`、改 `resolution_date`、改 `base_rate_value` 一律拒绝。

### 3.3 基础率来源非空

```sql
CONSTRAINT base_rate_source_required CHECK (length(trim(base_rate_source)) > 0)
```

理由写在注释里：标记 comparison class（基础率）的预测平均 Brier = 0.17，
次好标签 0.26。**这是实证里最大的单点提升，所以设为非空约束而非建议。**

### 3.4 影子权重晋升必须有 Outcome 背书

```sql
CONSTRAINT promotion_requires_outcome
    CHECK (promoted_at IS NULL OR validated_by_outcome IS NOT NULL)
```

人一否决权重立刻改，但此时还没有真实 Outcome 验证这次否决是不是对的。
不加这条约束，系统学到的只是当下偏见，不是市场真相。

流程：否决 → 写 `is_shadow=true` 的影子记录 → 等 Outcome →
方向验证正确才 `promoted_at` 写入正式权重；错了写 `discarded_reason`。

### 3.5 ¼ Kelly 上限写进数据库

```sql
kelly_fraction numeric CHECK (kelly_fraction IS NULL OR kelly_fraction BETWEEN 0 AND 0.25)
```

Kelly 对胜率估计误差极度敏感 —— 高估 2 倍胜率会导致长期资本归零。
所以上限写进数据库，而不是只写在代码里。

### 3.6 爬取源永不放行

```sql
CONSTRAINT scraping_never_cleared
    CHECK (NOT (access_method = 'scraping' AND legal_status = 'cleared'))
```

依据：2011–2022 的 12 起"爬虫+不正当竞争"案，**爬取方胜诉率不到 16.67%**；
2025 年《反不正当竞争法》新增数据专款第 13 条第 3 款。

这条约束把"优先用官方 API"从文档承诺变成数据库不变式。

### 3.7 假设必须可证伪

```sql
CONSTRAINT must_be_falsifiable CHECK (length(trim(falsifiable_when)) > 0)
```

"这个赛道有机会"不是假设。"如果 100 个目标用户里留资低于 15 个，
这个痛点就是假的"才是假设。

### 3.8 审计日志只可追加

```sql
CREATE TRIGGER audit_log_no_update BEFORE UPDATE OR DELETE ON audit_log ...
    RAISE EXCEPTION '审计日志只可追加，不可 % —— 可篡改的日志不是审计', TG_OP;
```

---

## 四、预测存档格式（JSONL 导出）

```json
{"opportunity_id": "OPP-001",
 "predicted_at": "2026-08-04",
 "base_rate": {"value": 0.12, "source": "同类目90天存活率"},
 "prediction": {"p10": 0.05, "p50": 0.23, "p90": 0.51},
 "category": "户外露营",
 "engine_version": 1,
 "aggregation_note": "logit-pool a=1.5, 3 sources, disagreement=0.42",
 "resolution_date": "2026-11-03",
 "actual_outcome": null}
```

`actual_outcome` 为 `null` 的条目**不参与校准，不做任何插补**。
`python -m oic.calibration.report --forecasts <path>` 会明确报告未解析条数。

---

## 五、多租户隔离

用 Supabase RLS 在**数据库层**强制隔离，而不是靠应用层记得加 `WHERE tenant_id = ...`：

```sql
ALTER TABLE opportunity ENABLE ROW LEVEL SECURITY;
CREATE POLICY opportunity_tenant_isolation ON opportunity
    USING (tenant_id::text = current_setting('app.tenant_id', true));
```

已启用 RLS 的表：`opportunity`、`portfolio_position`、
`weight_correction`、`passive_signal`。

> 落地时需按实际鉴权方案调整 `current_setting` 的键名。

---

## 六、赛道配置层（换赛道 = 改一个字符串）

赛道相关的一切放 `oic/config.py::TrackProfile`，计算代码完全赛道无关：

| 字段 | 爆品选品（默认） | AI 工具/SaaS |
|---|---|---|
| `outcome_label` | 上架 90 天后月销 ≥500 单 | 60 天内 MRR ≥2 万元 |
| `resolution_days` | 90 | 60 |
| `surrogate_label` | 落地页 7 天留资率 ≥15% | 候补名单 14 天 ≥200 人 |
| `base_rate_prior` | 0.12 | 0.08 |
| `stage_gates` | 选品验证/小批量试销/规模化/品牌化 | MVP/种子验证/付费转化/规模化 |

`outcome_label` 同时写进 `outcome.label_definition` 字段 —— **防口径事后漂移**。
