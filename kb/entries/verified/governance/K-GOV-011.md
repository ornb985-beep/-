---
id: K-GOV-011
title: 失效模式5：Kelly 在胜率未知时会主动伤人
domain: governance
type: antipattern
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/07-路线图与回退规则.md
  - oic/scoring/kelly.py
  - db/schema.sql
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

Kelly 对胜率误差极敏感：真实 20% 误估为 40%，长期增长率转负。它不是「不够好」，是**会主动把人打穿**。

## 依据

三重安全阀：Wilson 下界（非点估计）、¼ Kelly 上限、样本 <30 直接拒绝。¼ 上限同时写进数据库 CHECK 约束 —— 代码可以绕过，DB 约束不能。

## 边界：什么情况下它不成立

三重安全阀让 Kelly 变保守，但保守的 Kelly 仍然依赖胜率估计。样本足够之前，它的正确行为就是拒绝。

## 代码位置

`oic/scoring/kelly.py`（`MAX_KELLY_FRACTION = 0.25`）
