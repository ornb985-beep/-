---
id: K-GOV-002
title: G1 区分度门：指标不得塌缩成同一档
domain: governance
type: criterion
maturity: prior
status: active
evidence_grade: B
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/00-总纲与终局判据.md
  - docs/v4/05-Eval与门禁.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

≥5 个品类之间，剪刀差 M / 切换势能 / 成熟度 L 必须分出不同档位。全塌在同一档 = 这个指标废了。

## 依据

无区分度的指标不会报错，只会安静地让所有候选看起来一样 —— 这种失败比崩溃更危险，因为它看上去在正常工作。

## 边界：什么情况下它不成立

区分度不等于有效性。指标可以既有区分度又与结局无关 —— 那正是当前需求增速的状况（ρ=+0.058）。
