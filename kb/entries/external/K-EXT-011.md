---
id: K-EXT-011
title: 工具定义的质量决定 agent 的上限
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

工具的命名、参数设计、错误消息质量，对 agent 表现的影响大于提示词。

## 依据

模型只能通过工具描述理解工具。描述含糊时，它会用错或不用。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

工具太多会稀释选择准确率。「把所有能力都做成工具」是常见的反模式。
