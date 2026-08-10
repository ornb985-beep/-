---
id: K-CMP-020
title: 爬取禁令同时写进数据库 CHECK
domain: compliance
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - db/schema.sql
  - oic/compliance/provenance.py
  - docs/v4/03-数据契约与Schema.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`access_method = SCRAPING` 的记录不可能有 `legal_status = cleared`，由 CHECK 约束保证。

## 依据

代码闸可以被新写的代码路径绕过；数据库 CHECK 不能 —— 任何路径的写入都会被拒绝。两层的意义在于「以后有人不知道这条规则时也拦得住」。

## 边界：什么情况下它不成立

CHECK 只管数据库里的记录。完全不走数据库的临时脚本仍然可以自己发请求。

## 代码位置

`db/schema.sql`
