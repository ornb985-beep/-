---
id: K-ANA-002
title: 红线一票归零，不可被高分抵消
domain: analysis
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/scoring/redlines.py
  - docs/v4/02-公式与算法规范.md
  - tests/test_scoring.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

任一红线触发 → 红线因子 = 0 → 排序分归零。

## 依据

红线是「无论其他多好都不做」的事。做成可加权会让它在实践中被高分淹没。

## 边界：什么情况下它不成立

红线的阈值本身是 PRIOR。阈值定错会导致误杀，而误杀正是历史上导致团队关掉闸门的主因。

## 代码位置

`oic/scoring/redlines.py::evaluate`
