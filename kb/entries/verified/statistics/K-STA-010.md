---
id: K-STA-010
title: Kelly 用 Wilson 下界而非点估计
domain: statistics
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/scoring/kelly.py
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

胜率取 Wilson 区间下界（z=1.2816，80%），不用样本比例点估计。

## 依据

小样本的胜率点估计系统性偏乐观。Kelly 对胜率高估极敏感：真实 20% 误估为 40%，长期增长率转负。

## 边界：什么情况下它不成立

Wilson 下界让仓位偏保守。在胜率确实很高时会低估最优仓位 —— 这个代价是刻意付的。

## 代码位置

`oic/scoring/kelly.py::wilson_lower_bound`
