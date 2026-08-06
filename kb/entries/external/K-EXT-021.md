---
id: K-EXT-021
title: 数值计算不应交给语言模型
domain: external
type: criterion
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

算术、统计、单位换算应当交给确定性代码，模型只负责抽取输入。

## 依据

模型的数值计算错误不会报错，只会给出一个看起来合理的数。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

这正是本系统铁律 1 的外部对应：把计算与判断物理隔离是通行做法，不是本项目独创。
