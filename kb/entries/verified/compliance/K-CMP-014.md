---
id: K-CMP-014
title: 预测一旦写入不可修改
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

Prediction 表禁止 UPDATE 关键字段。

## 依据

可修改的预测让校准失去意义 —— 事后微调预测值可以让任何系统看起来校准良好。

## 边界：什么情况下它不成立

需要更新时应当写入新预测并保留旧记录，由 `SCORING_ENGINE_VERSION` 区分。

## 代码位置

`db/schema.sql`
