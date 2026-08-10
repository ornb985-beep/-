---
id: K-EXT-015
title: 生产环境需要记录完整的输入输出以便回溯
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

记录每次调用的提示词、模型版本、参数与输出，供事后归因。

## 依据

模型行为会随版本变化。没有记录就无法判断「上周还好好的」是模型变了还是数据变了。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

记录会包含用户数据，需要与隐私合规要求协调。本系统的做法是记录 span 与哈希而非全文。
