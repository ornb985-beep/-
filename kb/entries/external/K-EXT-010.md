---
id: K-EXT-010
title: Agent 应当有明确的终止条件与迭代上限
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

自主 agent 必须定义什么算完成、最多迭代几次，超限即停并如实报告。

## 依据

没有上限的 agent 会在失败任务上无限消耗预算，且往往越试越偏。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

上限设得太低会让本可完成的任务失败。上限应当按任务类型实测确定，不是拍一个数。
