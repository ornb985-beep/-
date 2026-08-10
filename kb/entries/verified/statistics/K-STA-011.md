---
id: K-STA-011
title: ¼ Kelly 上限，且写进数据库 CHECK
domain: statistics
type: parameter
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 4
sample_size:
sources:
  - oic/scoring/kelly.py
  - db/schema.sql
  - docs/v4/03-数据契约与Schema.md
  - tests/test_scoring.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`MAX_KELLY_FRACTION = 0.25`，同时作为数据库 CHECK 约束。

## 依据

全 Kelly 的破产风险在胜率估计有误时极高。写进 DB CHECK 是因为**代码可以被绕过，数据库约束不能** —— 任何路径写入超过 ¼ 的仓位都会被拒绝。

## 边界：什么情况下它不成立

¼ 是业界常用的保守系数，不是从本项目数据推出的。标 PRIOR。

## 代码位置

`oic/scoring/kelly.py` 的 `MAX_KELLY_FRACTION`
