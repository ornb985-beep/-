---
id: K-EXT-018
title: 长上下文不等于可以省掉检索
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

即使模型支持很长的上下文，把全部资料塞进去仍然不如先检索再注入。

## 依据

长上下文中间位置的信息容易被忽略，且成本随长度线性增长。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

对确实需要全局理解的任务（如整篇文档的一致性检查），长上下文是必要的。
