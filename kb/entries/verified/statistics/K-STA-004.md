---
id: K-STA-004
title: 多重检验必须做 Benjamini-Hochberg 校正
domain: statistics
type: method
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/stats/overfit.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

同时检验多个特征时，用 BH 控制错误发现率，而不是逐个看 p<0.05。

## 依据

测 20 个特征，最好的那个必然好看 —— 纯属偶然。这是量化金融最核心的教训之一，且有成熟解法。

## 边界：什么情况下它不成立

BH 控制的是 FDR 不是 FWER，允许一定比例的假阳性。在探索阶段这个取舍是合理的，在确认阶段应当更严。

## 代码位置

`oic/stats/overfit.py::benjamini_hochberg`
