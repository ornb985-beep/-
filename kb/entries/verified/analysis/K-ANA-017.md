---
id: K-ANA-017
title: 真实性系数下限 0.5，不允许单一代理打死商机
domain: analysis
type: parameter
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

`真实性系数 = 1 − min(刷单风险分/100 × k, 0.5)`，k=1.0。**下限 0.5。**

## 依据

第三方拿不到平台级反作弊信号（设备指纹、关系网络），所以这只是「真实性置信度」，不是确定结论。把商机直接打死是 R5 红线的职责，不是一个代理指标的职责。

## 边界：什么情况下它不成立

k 与下限都是 PRIOR。如果某天能拿到平台级信号，这条应当重新设计而不是调参。

## 代码位置

`oic/scoring/engine.py::authenticity_coefficient`
