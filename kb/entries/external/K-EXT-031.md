---
id: K-EXT-031
title: 检索的召回比精度更值得优先优化
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

检索不到的内容，后续任何步骤都补救不了；检索到多余的内容，模型通常能忽略。

## 依据

召回失败是无声的 —— 没人知道有一条关键资料没被检索到。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

召回过高会拉长上下文并稀释注意力。这个取舍点取决于模型对噪声的容忍度。
