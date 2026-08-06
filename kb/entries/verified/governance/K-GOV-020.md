---
id: K-GOV-020
title: 回退：span 丢弃率过高改提示词不放宽校验
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

**触发条件**：grounding span 丢弃率 >30%

**动作**：改抽取提示词或 schema，**不放宽校验**

触发即执行，不讨论。

## 依据

放宽校验会让幻觉通过，而丢弃率高说明抽取方式错了

## 边界：什么情况下它不成立

回退规则的价值在于事前写死。事到临头再讨论，讨论的结果一定是「这次情况特殊」。
