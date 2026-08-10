---
id: K-CMP-021
title: 输出路径上的三道闸
domain: compliance
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/06-合规内核.md
  - oic/sdk.py
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

证券边界 → AI 双标识 → 标识校验。三道全过才允许导出。

## 依据

把三道闸串在**唯一出口**上，而不是要求调用方记得依次调用。

## 边界：什么情况下它不成立

三道闸都不检查内容的事实正确性。那由证据层与纠错层在更早的阶段负责。

## 代码位置

`oic/sdk.py::OIC.export`
