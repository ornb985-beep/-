---
id: K-ORC-007
title: 诚实计数：宁可报少，不许凑数
domain: orchestration
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 1
sample_size:
sources:
  - oic/pipeline/budget.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`honest_count()` 如实上报「今日可用 N 条、实际处理 M 条、因配额未处理 K 条」。超预算时 `consume()` 抛 `BudgetExhausted` 而不是降级。

## 依据

真正危险的不是「处理得少」，是「处理得少却报成处理得多」。前者是产能问题，后者是数据污染 —— 它会让后面所有统计建在虚数上。

## 边界：什么情况下它不成立

在无限配额下这条几乎不触发。但它必须留着，因为**总有一天会给某个部署设上限**。

## 代码位置

`oic/pipeline/budget.py::honest_count`
