---
id: K-EXT-012
title: 错误消息应当告诉 agent 下一步怎么做
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

工具返回错误时，消息里应包含可执行的修正建议，而不只是「参数非法」。

## 依据

agent 只能从错误消息里学。信息量不足的错误消息会导致重复同样的错误。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

过于具体的建议可能把 agent 引向错误方向。建议应当描述约束，而不是替它做决定。
