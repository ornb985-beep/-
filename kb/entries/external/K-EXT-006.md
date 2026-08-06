---
id: K-EXT-006
title: 小模型做路由，大模型做判断
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

用便宜模型做分类与路由，把昂贵模型留给真正需要推理的少数样本。

## 依据

大部分请求的难度远低于最难的那部分，用同一个模型处理是浪费。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

路由错误的代价不对称：把难样本路由给小模型的损失，远大于把易样本路由给大模型的浪费。路由阈值应当偏保守。
