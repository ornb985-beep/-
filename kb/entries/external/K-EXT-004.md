---
id: K-EXT-004
title: 提示缓存能大幅降低重复前缀的成本
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

把稳定不变的前缀（系统提示、工具定义、长文档）做缓存，只为变化部分付全价。

## 依据

多轮对话与批处理场景里，前缀往往占 token 的绝大部分。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

缓存有生命周期，且要求前缀逐字节一致。前缀里放了时间戳之类的变量会让缓存全部失效。
