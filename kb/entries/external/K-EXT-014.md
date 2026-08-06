---
id: K-EXT-014
title: 评测集必须与训练/调优过程隔离
domain: external
type: method
maturity: external
status: active
evidence_grade: B
n_independent_sources: 1
sample_size:
sources:
  - EXT:业界通行实践
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

用于报告成绩的评测集不得参与任何提示词调优或特征选择。

## 依据

在同一批数据上反复调优再报告成绩，报出来的是拟合优度。这与本系统的 Purged CV 是同一个道理。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

小团队常常只有一批标注数据。那时应当切分并锁住测试集，而不是「反正数据少就一起用」。
