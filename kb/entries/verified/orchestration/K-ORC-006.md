---
id: K-ORC-006
title: 价值分流：付不起就如实标未处理，不降标准
domain: orchestration
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/pipeline/budget.py
  - docs/v4/12-无限检索与智能体集群.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

按分数降序排，能付得起多少就升级多少。**剩下的如实标为「未处理」。**

## 依据

两件它明确不做的事：不因为配额不够就降低标准去处理更多条；不假装未处理的那些「已评估过」。

## 边界：什么情况下它不成立

`ESCALATION_PERCENTILE = 0.8` 是 PRIOR 值，未经校准。分位阈值本身还需要真实数据来定。

## 代码位置

`oic/pipeline/budget.py::select_for_escalation`
