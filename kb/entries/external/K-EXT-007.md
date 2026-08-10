---
id: K-EXT-007
title: Self-consistency：多次采样取众数
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

对同一问题多次采样，取出现最多的答案，可提升推理任务准确率。

## 依据

单次采样受随机性影响；多数投票能滤掉部分随机错误。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

**它滤不掉系统性错误** —— 如果模型对某类问题一贯错，投十次仍然错十次，而且看起来非常一致。
