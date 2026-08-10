---
id: K-STA-005
title: 回测过拟合概率 PBO 是必测项
domain: statistics
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/stats/overfit.py
  - docs/v4/05-Eval与门禁.md
  - tests/test_research.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

用 CSCV 计算 Probability of Backtest Overfitting。有一条测试断言：20 个特征 × n=8 时必须报出高 PBO。

## 依据

「回测好看」和「样本外有效」之间隔着过拟合。PBO 把这个距离量化，让「我们回测很好」这句话变得可检验。

## 边界：什么情况下它不成立

PBO 需要足够的数据切分。本项目当前样本量下它主要起警示作用 —— 它会告诉你「这个样本量下别下结论」。

## 代码位置

`oic/stats/overfit.py::probability_of_overfit`
