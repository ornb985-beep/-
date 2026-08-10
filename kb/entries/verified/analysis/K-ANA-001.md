---
id: K-ANA-001
title: 主排序公式
domain: analysis
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/scoring/engine.py
  - docs/v4/02-公式与算法规范.md
  - tests/test_scoring.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`排序分 = 总分 × 变现系数 × M系数 × 风险系数 × 真实性系数 × 红线因子`。

## 依据

乘法结构让每个系数都有一票否决的能力（乘 0 即归零），同时保证每个分数都能展开成一行可复算算式。

## 边界：什么情况下它不成立

乘法也意味着系数之间无法互补 —— 一个很高的总分救不回一个 0.7 的 M 系数。这是刻意的。

## 代码位置

`oic/scoring/engine.py::compute_all_scores`
