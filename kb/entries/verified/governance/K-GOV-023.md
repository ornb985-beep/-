---
id: K-GOV-023
title: 回退：代理结局不过 Prentice 即停用
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

**触发条件**：代理结局未通过 Prentice 准则

**动作**：停用该代理写入校准

触发即执行，不讨论。

## 依据

不满足 Prentice 的代理会把校准往错误方向拉

## 边界：什么情况下它不成立

回退规则的价值在于事前写死。事到临头再讨论，讨论的结果一定是「这次情况特殊」。
