---
id: K-ANA-008
title: C/O/D/E 四维权重基准 25、上限 40
domain: analysis
type: parameter
maturity: prior
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/config.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

四维权重基准均为 25，公式系数 = 基准系数 × (权重/25)，单维上限 40。

## 依据

上限存在是为了防止一次误否决把某一维推到支配地位 —— 影子权重机制会随反馈调整权重，没有上限时它会失控。

## 边界：什么情况下它不成立

**四维本身从未被证明有预测力**（失效模式 1）。权重调优是在一个未验证的特征集上做微调。

## 代码位置

`oic/config.py::Weights`
