---
id: K-DLV-008
title: Outcome 是系统命门
domain: delivery
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/03-数据契约与Schema.md
  - docs/v4/07-路线图与回退规则.md
  - data/research/FINDINGS.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

Outcome 表为空时，七个模块（Brier/Murphy/BSS/分层贝叶斯/共形/Kelly/CATE）全部无法运行。当前已解析 11 条。

## 依据

**今天开始记，永远补不回来。** 结局数据有时效性 —— 错过的窗口无法回溯采集。这是整个系统里唯一「不做就永久损失」的事。

## 边界：什么情况下它不成立

已解析 11 条不等于记录了 11 条。记录更多但未解析的结局仍然有价值，它们会随时间自然解析。

## 代码位置

`db/schema.sql`
