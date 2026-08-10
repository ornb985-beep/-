---
id: K-CMP-013
title: 审计日志只可追加
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

审计表用数据库触发器阻止 UPDATE 与 DELETE。

## 依据

可修改的审计日志等于没有审计日志。做成数据库级约束是因为应用层代码总有绕过的路径。

## 边界：什么情况下它不成立

只可追加意味着错误记录也会永久留存。更正的方式是追加一条更正记录，而不是改原记录。

## 代码位置

`db/schema.sql`
