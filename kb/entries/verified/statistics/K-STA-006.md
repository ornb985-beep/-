---
id: K-STA-006
title: Purged / 留一交叉验证防止选特征与报成绩用同一批数据
domain: statistics
type: method
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/02-公式与算法规范.md
  - oic/stats/overfit.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

特征选择与成绩报告必须用不同的数据切分。

## 依据

用同一批数据既选特征又报成绩，报出来的是拟合优度不是预测力。时间序列还需 purge 掉切分边界附近的样本以防信息泄漏。

## 边界：什么情况下它不成立

留一 CV 在极小样本下方差很大。它给出的是「不至于自欺」的下限，不是精确的泛化误差估计。
