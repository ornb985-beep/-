---
id: K-MET-003
title: 跨 Scope 合并一律拒绝
domain: metrics
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/research/metrics.py
  - tests/test_research.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`Scope` 不同的观测不允许进入同一次聚合，包括 ALL / CORE / DRIVEN / B2B / B2C / RETAIL / EQUIPMENT。

## 依据

带动市场规模通常远大于核心市场规模（有时数倍）。把两者平均得到的数字既不是核心也不是带动，是个没有含义的数。

## 边界：什么情况下它不成立

跨 Scope 的**比较**是有意义的（比如算 B2B 占比）。被禁止的是把它们当成同一指标的多个观测去平均。

## 代码位置

`oic/research/metrics.py::Scope`
