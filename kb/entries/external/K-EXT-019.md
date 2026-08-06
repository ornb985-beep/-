---
id: K-EXT-019
title: 模型版本升级需要重跑评测而不是假设更好
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

更换模型版本后应当重跑完整评测，不能假设新版本在本任务上更强。

## 依据

总体基准提升不保证特定任务提升，且提示词可能对旧版本过拟合。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

重跑评测有成本。至少应当跑对抗集与关键回归用例。
