---
id: K-EXT-017
title: 温度调低不等于更可靠
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

降低采样温度会让输出更确定，但不会让错误的答案变正确。

## 依据

低温只是让模型更坚定地给出它最可能的答案 —— 包括错误答案。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

在需要多样性的场景（如生成候选方案）低温反而有害。
