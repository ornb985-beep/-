---
id: K-EXT-027
title: 对抗样本应当来自真实失败而非人工构造
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

评测里的困难样本应当从生产失败中收集，而不是凭想象构造。

## 依据

人工构造的对抗样本反映的是构造者的想象力，不是真实失败分布。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

生产失败的收集需要有反馈渠道。冷启动时只能先用构造样本。
