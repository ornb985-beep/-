---
id: K-ANA-003
title: 红线 R1：已确认的合规问题
domain: analysis
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/scoring/redlines.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

**触发条件**：`compliance_flags` 命中任一已知类别 → 排序分归零。

## 依据

合规问题不是风险而是禁止项，落地前须经执业律师审查

## 边界：什么情况下它不成立

阈值为 PRIOR，未经真实数据校准，界面必须显示「未校准」。

## 代码位置

`oic/scoring/redlines.py`
