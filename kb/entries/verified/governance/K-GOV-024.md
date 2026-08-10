---
id: K-GOV-024
title: 回退：污染检测误报多即保持关闭
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

**触发条件**：污染检测误报数 > 真报数

**动作**：保持 `enabled=false`

触发即执行，不讨论。

## 依据

误报会让团队关掉整道闸，代价远大于漏报

## 边界：什么情况下它不成立

回退规则的价值在于事前写死。事到临头再讨论，讨论的结果一定是「这次情况特殊」。
