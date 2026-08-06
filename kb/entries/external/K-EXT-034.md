---
id: K-EXT-034
title: 失败要快且可见，不要静默降级
domain: external
type: criterion
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

AI 组件失败时应当明确报错，而不是返回一个看起来正常的降级结果。

## 依据

静默降级会让错误进入下游并被当成正常数据，而且往往在很久之后才以难以归因的形式暴露。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

在用户面向的场景，明确报错会影响体验。折中是报错但给出可操作的下一步，而不是假装成功。
