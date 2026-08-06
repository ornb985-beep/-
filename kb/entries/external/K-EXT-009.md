---
id: K-EXT-009
title: LLM-as-judge 需要独立评审与人工锚定
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

用模型评估模型输出时，评审模型应当独立于生成模型，且需定期用人工标注锚定。

## 依据

同模型自评存在系统性偏好（倾向给自己的输出打高分）。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

即使独立，模型评审也有位置偏好、长度偏好等系统性偏差。**它不能替代人工标注，只能扩大人工标注的覆盖。**
