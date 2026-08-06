---
id: K-GOV-018
title: 回退：单 agent 基线 ≥45% 时不扩 agent
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

**触发条件**：单 agent 实测准确率 ≥45%

**动作**：不扩 agent，改优化提示词与验证

触发即执行，不讨论。

## 依据

Google+MIT 的 45% 规则：过了这个点加 agent 收益递减甚至转负

## 边界：什么情况下它不成立

回退规则的价值在于事前写死。事到临头再讨论，讨论的结果一定是「这次情况特殊」。
