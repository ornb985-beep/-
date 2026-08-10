---
id: K-STA-018
title: 剪刀差方向转正但未达判据，且没打过运气基线
domain: statistics
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size: 5
sources:
  - data/research/FINDINGS.md
  - oic/research/backtest.py
  - oic/stats/overfit.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

n=5：ρ = **+0.289**，AUC = **0.667**（cohort1 单独时为 0.000 与 0.500）。判据 |ρ|>0.3 **未达**；且 n=5 时纯随机 |ρ| 中位数约 0.4，**连运气基线都没打过**。

## 依据

方向从 0 转为正，与理论预期一致（剪刀差越大越好）。这**不构成有效性证据**，只说明这条线值得继续扩样本去测 —— 而需求增速那条已经被扩样本否掉了。两者现在有了区别。

## 边界：什么情况下它不成立

n=5 且样本来自两个不同 cohort，可比性本身存疑。
