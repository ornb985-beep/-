---
id: K-EXT-001
title: 结构化输出优于自由文本解析
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

让模型直接产出受约束的结构（JSON Schema / 工具调用），而不是生成自由文本再正则解析。

## 依据

自由文本解析的失败模式是无声的：格式稍变，正则就静默匹配不到。结构化输出把这类失败提前到生成阶段。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

结构约束会限制模型表达复杂或例外情况的能力，可能逼它把不确定的内容硬塞进固定字段。
