---
id: K-STA-001
title: 小样本用精确置换检验，不用正态近似
domain: statistics
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/stats/resample.py
  - docs/v4/02-公式与算法规范.md
  - tests/test_research.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

n 小到可穷举时，`permutation_test_binary` 枚举全部排列给出**精确** p 值。

## 依据

n=7 时正态近似完全失效。本项目实测：穷举 35 种排列得到 p=0.629，这是精确值不是近似值。

## 边界：什么情况下它不成立

n 稍大时穷举不可行，需退回蒙特卡洛置换。那时 p 值有采样误差，应报告重复次数。

## 代码位置

`oic/stats/resample.py::permutation_test_binary`
