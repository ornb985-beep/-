---
id: K-CMP-019
title: 影子权重晋升必须有 Outcome 背书
domain: compliance
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - db/schema.sql
  - docs/v4/03-数据契约与Schema.md
  - docs/v4/09-方案融合与缺口.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

影子权重要转正，必须有真实结局数据支撑。

## 依据

没有结局背书的权重调整，学到的是**当下的偏见**而不是市场真相 —— 系统会越来越擅长复现历史推荐，而不是预测未来。

## 边界：什么情况下它不成立

这条把权重学习整体锁在 Wave 4 之后。在此之前所有权重保持 PRIOR。

## 代码位置

`db/schema.sql`
