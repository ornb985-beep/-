---
id: K-EXT-033
title: 同一提示词在不同模型上的表现不可迁移
domain: external
type: lesson
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

为某个模型调优的提示词换到另一个模型上可能显著变差。

## 依据

提示词调优本质上是在拟合特定模型的行为分布。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

这让「换模型」的成本远高于改一行配置。换模型应当当作一次需要重新评测的变更。
