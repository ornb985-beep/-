---
id: K-ORC-008
title: 不限成本 ≠ 不计数
domain: orchestration
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/pipeline/budget.py
  - docs/v4/12-无限检索与智能体集群.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`DailyCaps` 默认全部 `UNLIMITED = 2⁶²`，但 `Ledger` 照常记账。取消的是上限，不是计数。

## 依据

「花了多少」和「拿到多少」的比值，是判断某个角度还值不值得继续查的唯一依据。把计数一起去掉，饱和度判据就没有输入了。

## 边界：什么情况下它不成立

记账本身有极小的开销。在真正的高频场景可以采样记账，但不能完全关闭 —— 关掉就等于关掉了饱和度判定。

## 代码位置

`oic/pipeline/budget.py::DailyCaps`（默认 UNLIMITED）
