---
id: K-DLV-004
title: 反证条件必须在 14 天内可判定
domain: delivery
type: criterion
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 2
sample_size:
sources:
  - oic/deliver/plan_90day.py
  - docs/v4/08-操盘手全流程.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

每条假设的反证条件应当在两周内产生可观测信号。

## 依据

反证条件如果 90 天后才能判定，它就不是止损线，是事后总结。两周是让「早点知道错了」这件事真正发生的量级。

## 边界：什么情况下它不成立

有些假设本质上需要更长周期验证。那时应当找一个可在 14 天内观测的**代理指标** —— 并接受 Goodhart 风险（见失效模式 4）。

## 代码位置

`oic/deliver/plan_90day.py`
