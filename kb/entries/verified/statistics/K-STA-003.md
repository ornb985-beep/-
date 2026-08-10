---
id: K-STA-003
title: 先算运气基线，再看结果好不好看
domain: statistics
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/stats/overfit.py
  - data/research/FINDINGS.md
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`expected_max_correlation()` 给出「纯随机情况下最好的那个特征能有多好看」。观测值打不过这个基线，就不构成发现。

## 依据

n=7 时纯随机的 |ρ| 中位数就是 **0.289** —— 与本项目当时观测到的 ρ=−0.289 完全相同。n=5 时约 0.4，而剪刀差观测到 0.289，**连运气基线都没打过**。

## 边界：什么情况下它不成立

运气基线依赖对「测了多少个特征」的诚实计数。如果实际尝试过的特征比声称的多，基线会被低估。

## 代码位置

`oic/stats/overfit.py::expected_max_correlation`
