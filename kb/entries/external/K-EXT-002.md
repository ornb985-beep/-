---
id: K-EXT-002
title: 检索增强（RAG）把知识与参数解耦
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

把易变知识放在检索层而非模型权重里，通过检索注入上下文。

## 依据

知识更新不需要重训；且检索结果可以作为引用出处呈现给用户。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

检索质量决定上限。检索不到或检索错了，模型会用参数里的旧知识补，而且看不出来 —— 这正是本系统坚持字符级 grounding 的原因。
