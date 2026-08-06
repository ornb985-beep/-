---
id: K-EXT-025
title: 确定性种子不能保证 LLM 输出可复现
domain: external
type: fact
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

即使固定种子与温度，分布式推理的浮点非确定性仍可能导致输出不同。

## 依据

这是本系统把可复现性要求**完全放在确定性代码层**的根本原因 —— 不指望模型输出可复现。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

某些推理配置下可以做到近似可复现，但不应作为架构假设。
