---
id: K-CMP-004
title: 证券边界 S3：给出买卖时机
domain: compliance
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/compliance/securities_guard.py
  - docs/v4/06-合规内核.md
  - tests/test_compliance.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

**命中即阻断输出，且不做自动改写。** 检测范围：买入时机/时点/信号/点位，或「现在正是入场」类表述。

## 依据

命中荐股软件认定标准③

## 边界：什么情况下它不成立

**不自动改写**是刻意的：改写会掩盖问题，而这类内容根本不该被生成出来。改写只会让下一次生成得更隐蔽。

## 代码位置

`oic/compliance/securities_guard.py` 的 `_RULES`
