---
id: K-GOV-019
title: 回退：顺序推理任务一律不扩 agent
domain: governance
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 1
sample_size:
sources:
  - docs/v4/07-路线图与回退规则.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

**触发条件**：任务是顺序推理链而非可并行子任务

**动作**：一律不扩

触发即执行，不讨论。

## 依据

实测倒退 39–70%，不是收益变小而是变负

## 边界：什么情况下它不成立

回退规则的价值在于事前写死。事到临头再讨论，讨论的结果一定是「这次情况特殊」。
