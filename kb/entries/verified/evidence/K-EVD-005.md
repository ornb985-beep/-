---
id: K-EVD-005
title: 证据有时效，越旧权重越低
domain: evidence
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 2
sample_size:
sources:
  - oic/evidence/decay.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

证据按发布时间衰减，旧证据在合并时权重更低。

## 依据

商业数据的半衰期很短。2019 年的市占率对 2025 年的决策价值有限，但把它和新数据等权平均会把结论往过去拉。

## 边界：什么情况下它不成立

衰减系数是 PRIOR 值，未经真实数据校准。不同品类的实际半衰期差别可能很大。

## 代码位置

`oic/evidence/decay.py`
