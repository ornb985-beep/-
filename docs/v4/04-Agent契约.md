# 04 · Agent 契约

> ⚠️ **本层当前被铁律 2 阻塞。**
> `oic.config.AgentGate.multi_agent_allowed()` 在 `baseline_accuracy is None`
> 时恒为 `False`。本文档定义的是**解锁后**的契约，不是现在就该建的东西。

---

## 一、扩展门禁（先读这一节）

```python
gate = AgentGate(baseline_accuracy=None)      # 当前状态
gate.multi_agent_allowed()                    # → False
gate.reason()                                 # → "单 agent 基线未测量 —— 按铁律 2 禁止扩展多智能体"
```

| 前置条件 | 是否满足 |
|---|---|
| 已实测单 agent 准确率 | ❌ 未测 |
| 准确率 < 45% | — |
| 任务可拆成独立并行子任务 | — |

**三个条件全满足才允许扩展。** 依据（Kim et al., arXiv:2512.08296）：

- 单 agent 准确率超过约 45% 后，加 agent 收益递减甚至转负
- 顺序推理任务多智能体实测**倒退 39–70%**
- 并行任务（Finance Agent）Centralized 架构 **+80.8%**
- 最优规模 **3–4 个 agent**
- **5 个各 95% 可靠的 agent 串联 = 系统可靠性仅 77%**

**回退规则**：多 agent token >15× 但质量提升 <20% → 退回单 agent + CoVe。

---

## 二、通用契约

每个 agent 必须声明五项，缺一不可：

| 项 | 说明 |
|---|---|
| **输入** | 精确到字段。禁止"把上下文都给它" |
| **输出 schema** | Pydantic/JSON Schema 约束解码。**不做自由文本** |
| **done 条件** | 什么算完成。没有 done 条件的 agent 会无限循环 |
| **最大迭代** | 硬上限。超限即失败上报，不静默重试 |
| **模型档** | 固定档位，**不做动态路由分类器**（分类器本身会出错） |

### 关于重试

**重试率 ≥2 即报警改 schema，而不是加重试。**
反复重试说明输出 schema 与任务不匹配，加重试只是把问题变贵。

### 关于工具错误

工具错误必须原样返回给模型（而不是包装成友好文案）——
原始错误信息是模型自我纠正的最有效输入。

---

## 三、各 Agent 契约

### F3.1 Analyst（强档）

| 项 | 内容 |
|---|---|
| 输入 | 已锚定的证据集（`anchored=true`）+ **该品类基础率** |
| 输出 | `{c, o, d, e: 0-100, rationale_per_dim, cited_evidence_ids}` |
| done | 四维都有分且每维至少引用 1 条证据 id |
| 最大迭代 | 2 |

**强制基础率前置**：提示词必须以
`base_rate_for_prompt(estimate)` 的输出开头：

```
基础率：同类目（户外露营）历史成功率 12.3%（90% 区间 4.1%–24.7%，样本 n=5）。
请先以此为锚，再根据本商机的具体证据调整。
```

依据：标记 comparison class 的预测平均 Brier **0.17**，次好标签 0.26。
这是实证里最大的单点提升，成本只是改提示词。

### F3.3 Challenger（强档）

| 项 | 内容 |
|---|---|
| 输入 | **只有原始证据。不得传入 Analyst 的结论或分数** |
| 输出 | `{challenges: [{evidence_id, objection, severity}], missing_evidence: [...]}` |
| done | 至少检查完全部 A/B 级证据 |
| 最大迭代 | 1 |

**这是铁律 3 的落点。** factored CoVe：验证问题独立回答、不看原草稿。
长文本 FactScore 55.9 → 71.4；list QA precision 0.17 → 0.36。

**为什么必须独立**：多智能体辩论存在从众效应 —— 弱模型仅纠正 3.6% 立场偏差。
Challenger 看到 Analyst 说"这个赛道很好"之后，会倾向于只挑小毛病。

### F3.4 Pre-mortem（强档）

| 项 | 内容 |
|---|---|
| 输入 | 商机描述 + S2 作战计划草案（**不含分数**） |
| 输出 | `{failure_paths: [{stage, cause, early_signal, preventable}]}` |
| done | 至少给出 3 条失败路径，每条带可观测的早期信号 |
| 最大迭代 | 1 |

提示词骨架：**"假设 6 个月后这个商机彻底失败了。复盘：为什么？"**

与 Challenger 互补：Challenger 质疑**证据**，Pre-mortem 质疑**执行**。
两者属独立并行子任务，符合扩展条件。

### F3.5 Steelman（强档）

| 项 | 内容 |
|---|---|
| 输入 | 同 Pre-mortem |
| 输出 | `{case_against: str, strongest_alternative_use_of_capital: str}` |
| done | 给出"不做"的最强论证 + 这笔钱的最佳替代用途 |
| 最大迭代 | 1 |

**为什么需要**：防止 Challenger 流于挑刺。挑十个小毛病 ≠ 论证不该做。

### F3.2 Dissector（强档）

| 项 | 内容 |
|---|---|
| 输入 | 单品/品类的原始榜单数据 + 评论语料 |
| 输出 | 款词图价 + MEC 三层 + 卖家结构 + 生命周期阶段 + 刷单风险分 |
| done | 五项俱全 |
| 最大迭代 | 2 |

刷单风险分输出到 `fake_review_score`，>60 触发 R5 红线。

### F3.6 人群刻画（中档）

DMP 人货场 / 抖音 5A / 小红书生活方式三套模板作**提示词骨架**，不是 API 调用。

### F3.7 Self-consistency 投票

判断型任务多次采样 → `aggregate_probabilities()` 聚合。
**分歧度直接作为不确定性信号**：>1.0 触发强制人审 + 降置信度。

---

## 四、聚合与仲裁

多个 agent 的概率判断**不做算术平均**，走
`oic/scoring/aggregate.py::aggregate_probabilities`：

```
logit 平均 → extremization (a=1.5) → 分歧度检查
```

**冲突仲裁由确定性层做，不让 LLM 调和。**
MAST 研究显示"输出冲突"是多智能体主要失败模式之一。
红线判定、排序分计算全在 `oic/scoring/` 里，agent 无权改。

---

## 五、编排

- **主编排**：LangGraph（图状态机，非线性链）
- **长任务持久化**：Temporal（采集任务可能跑几小时，需要断点续跑）
- **约束解码**：Instructor / Pydantic —— 输出 schema 强制

### 分层路由（性能）

每个 agent **固定模型档**，不做动态路由分类器。
依据：RouteLLM 显示 14% 请求走强模型即可达 95% 质量，省 40–85% 成本。
但动态分类器本身会出错，固定档位更可控。

| 档 | 用途 |
|---|---|
| 便宜档 | 采集清洗、格式化、去重 |
| 中档 | 人群刻画、摘要 |
| 强档 | Analyst / Challenger / Pre-mortem / Steelman / Dissector |

### 价值分流

低价值商机走**单 agent 快筛**，只有入围的高价值商机才跑完整集群。
15× token 只花在值得的地方。

---

## 六、人机边界（不可越过）

系统**永不自动执行**以下动作，必须人工批准：

| 动作 | 理由 |
|---|---|
| 花钱（投广告、打样、采购） | `experiment.approved_by` 非空才能 `running` |
| 发布内容 | 声誉风险不可逆 |
| 联系真实用户 | PIPL + 骚扰风险 |
| 签署任何协议 | — |

系统**可以**自动做的：分析、评分、排序、生成实验设计草案、
生成作战计划草案、算仓位建议、触发止损**告警**（不是自动止损执行）。

---

## 七、输出前的强制闸门

任何面向用户的文本，导出前必须依次通过：

```python
text = securities_guard.assert_safe(text)              # 证券边界，命中即抛错
content = ai_labeling.label(text, provider, now_iso)   # AI 双标识
ai_labeling.assert_labeled(content)                    # 标识完整性
```

三道闸任一失败即阻断导出，不做降级放行。
