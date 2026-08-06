---
id: K-CMP-018
title: 基础率来源不得为空
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

任何基础率必须记录它的来源。

## 依据

没有来源的基础率通常是拍的。而基础率错了，后面所有贝叶斯更新都是错的。

## 边界：什么情况下它不成立

来源非空不保证来源可靠。可靠性由证据分级处理。

## 代码位置

`db/schema.sql`
