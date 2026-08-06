---
id: K-GOV-021
title: 回退：重试率过高改 schema 不加重试
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

**触发条件**：同一任务平均重试次数 ≥2

**动作**：改 schema，**不加重试**

触发即执行，不讨论。

## 依据

重试是在掩盖 schema 与模型能力不匹配，加重试只会让成本线性上升

## 边界：什么情况下它不成立

回退规则的价值在于事前写死。事到临头再讨论，讨论的结果一定是「这次情况特殊」。
