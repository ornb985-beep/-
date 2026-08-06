---
id: K-DLV-007
title: 平台动作要具体到「在哪做什么」
domain: delivery
type: method
maturity: implemented
status: active
evidence_grade: C
n_independent_sources: 2
sample_size:
sources:
  - oic/deliver/resourcing.py
  - docs/v4/08-操盘手全流程.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

输出「在哪个平台、做什么动作」而不是「做内容营销」。

## 依据

抽象建议无法执行也无法验证。具体动作才能对应到 14 天内可观测的信号。

## 边界：什么情况下它不成立

平台生态变化很快，具体建议的时效性短。这部分内容需要比其他部分更频繁地更新。

## 代码位置

`oic/deliver/resourcing.py`
