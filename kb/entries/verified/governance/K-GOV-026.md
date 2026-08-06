---
id: K-GOV-026
title: 这套设计能保证什么、不能保证什么
domain: governance
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/00-总纲与终局判据.md
  - docs/v4/07-路线图与回退规则.md
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

**能保证：可复现、可审计、不自欺。不能保证：预测准。**

## 依据

可复现由 G0 双跑验证；可审计由字符级 grounding + 不可变审计日志保证；不自欺由 20 条代码层拒绝条件保证。「准」由 G2 判定，而 G2 需要 30 条真实结局，当前 11 条。

## 边界：什么情况下它不成立

这句话本身不会随时间失效，但它的后半句会 —— G2 通过后应当由一条新条目取代它。
