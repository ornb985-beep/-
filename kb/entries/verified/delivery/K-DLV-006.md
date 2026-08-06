---
id: K-DLV-006
title: 资金按阶段给上限，不给总预算
domain: delivery
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 2
sample_size:
sources:
  - oic/deliver/resourcing.py
  - oic/deliver/plan_90day.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

分阶段资金上限与止损线绑定，而不是给一个总数。

## 依据

给总预算会让人一次性投入。分阶段上限强制在每个阶段结束时重新决策。

## 边界：什么情况下它不成立

分阶段的前提是每阶段有明确的判定标准。判定标准模糊时，分阶段会退化成分期打款。

## 代码位置

`oic/deliver/resourcing.py`
