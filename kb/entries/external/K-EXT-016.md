---
id: K-EXT-016
title: 流式输出改善体感但不改善质量
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

流式返回降低首字延迟，提升交互体验，但不改变最终内容质量。

## 依据

把流式当成性能优化会误判 —— 它优化的是感知延迟不是吞吐。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

流式输出让「输出前的闸门」难以实施：内容已经开始展示，再拦就晚了。**本系统的三道闸因此不兼容流式。**
