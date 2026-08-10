---
id: K-EXT-032
title: 向量检索与关键词检索应当混合
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

语义检索擅长同义改写，关键词检索擅长专有名词与精确数字。混合优于任一单独使用。

## 依据

专有名词与数字正是本系统最关心的内容，而它们恰恰是纯向量检索最容易失手的地方。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

混合需要融合排序策略，增加了系统复杂度与调参维度。
