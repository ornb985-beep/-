---
id: K-MET-009
title: 异常值用 MAD 而不是标准差
domain: metrics
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 1
sample_size:
sources:
  - oic/research/audit.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

与共识的偏离超过 3 倍中位绝对偏差（MAD）的观测标记为待人工复核。

## 依据

标准差本身会被异常值污染 —— 一个 100× 的错误会把标准差撑大，从而让它自己看起来不异常。MAD 对异常值稳健。

## 边界：什么情况下它不成立

n 很小时 MAD 也不稳定。当前观测密度下这条主要起提示作用，不作为阻断条件。

## 代码位置

`oic/research/audit.py::check_outliers`
