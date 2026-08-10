---
id: K-EXT-008
title: 思维链在复杂推理上有效，在简单任务上可能有害
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

让模型分步推理能提升复杂任务表现，但对简单分类任务可能引入不必要的错误。

## 依据

分步推理给了模型自我纠正的机会，也给了它把自己绕进去的机会。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

「一律加思维链」是常见的过度使用。该不该加应当按任务实测，不是默认开启。
