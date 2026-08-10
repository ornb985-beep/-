---
id: K-ANA-027
title: logit-pooling 聚合多个概率意见
domain: analysis
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 2
sample_size:
sources:
  - oic/scoring/aggregate.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

多个来源的概率意见在 logit 空间加权平均，而非算术平均。

## 依据

算术平均会把极端意见拉向中间，logit 空间的平均对「非常确定」的意见保留更多信息。

## 边界：什么情况下它不成立

聚合的前提是各意见近似独立。如果多个 agent 共享同一上下文，聚合只是在放大同一个判断。

## 代码位置

`oic/scoring/aggregate.py`
