---
id: K-EXT-024
title: 护栏应当在输入与输出两侧都做
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

只做输出过滤会浪费生成成本；只做输入过滤挡不住模型自发产生的问题内容。

## 依据

两侧都做的成本更高，但覆盖面完全不同。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

本系统当前只做输出侧三道闸。输入侧护栏尚未实现 —— 这是已知缺口。
