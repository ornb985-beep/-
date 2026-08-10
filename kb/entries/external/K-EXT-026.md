---
id: K-EXT-026
title: 成本估算要按 token 而不是按请求
domain: external
type: parameter
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

同样一次调用，长上下文的成本可能是短上下文的百倍。

## 依据

按请求数做预算会在长文档场景严重低估。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

输入与输出 token 单价不同，缓存命中的单价又不同。精确估算需要分开计。
