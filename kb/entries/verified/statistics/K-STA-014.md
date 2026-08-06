---
id: K-STA-014
title: Beta-Binomial 分层借力解决冷启动
domain: statistics
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 2
sample_size:
sources:
  - oic/calibration/hierarchical.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

品类内样本 <5 时完全依赖全局先验，随样本增加逐步向品类自身均值收缩。

## 依据

冷启动品类没有自己的数据，但全局数据可以借。部分池化在借力与保留品类差异之间给出了原则性的折中。

## 边界：什么情况下它不成立

借力的前提是品类之间确实可交换。如果某品类结构上就与其他不同，借来的先验会把它拉偏。

## 代码位置

`oic/calibration/hierarchical.py`
