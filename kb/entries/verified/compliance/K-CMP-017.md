---
id: K-CMP-017
title: 假设必须可证伪才允许写入
domain: compliance
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - db/schema.sql
  - docs/v4/03-数据契约与Schema.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

Hypothesis 表要求填写反证条件，缺失即拒绝写入。

## 依据

不可证伪的假设无法驱动实验，也无法被淘汰。它会永远留在系统里消耗资源。

## 边界：什么情况下它不成立

「可证伪」由人判断填写内容质量，数据库只能检查字段非空。

## 代码位置

`db/schema.sql`
