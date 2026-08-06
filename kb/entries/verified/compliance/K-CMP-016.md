---
id: K-CMP-016
title: 多租户用行级安全隔离
domain: compliance
type: method
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

所有业务表启用 RLS，按租户隔离。

## 依据

应用层过滤会因为一次遗漏的 WHERE 导致跨租户泄漏。RLS 把隔离下沉到数据库，遗漏时是查不到数据而不是查到别人的数据。

## 边界：什么情况下它不成立

RLS 需要正确设置会话变量。配置错误会导致查不到任何数据 —— 这是安全的失败方向。

## 代码位置

`db/schema.sql`
