---
id: K-STA-016
title: 需求增速与结局的相关性与噪声不可分
domain: statistics
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size: 11
sources:
  - data/research/FINDINGS.md
  - oic/stats/resample.py
  - oic/research/backtest.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

双队列合并 n=11：ρ = **+0.058**，精确置换检验 p = **0.931**，Bootstrap 90% 区间 [−0.527, +0.607]。**看不出信号。**

## 依据

cohort 1 单独时 ρ=−0.289、p=0.629。加入 cohort 2（13 个新品类）后**符号翻转，幅度塌到接近零，p 升到 0.93**。这正是噪声该有的行为。

## 边界：什么情况下它不成立

这条说的是「as-of 需求增速这一个特征」与「结局主标签」的关系。不能推广成「需求侧信息无用」—— 其他需求侧特征没测过。
