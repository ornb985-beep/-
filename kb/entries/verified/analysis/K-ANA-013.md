---
id: K-ANA-013
title: Ulwick 机会分 = 重要性 + max(0, 重要性 − 满意度)
domain: analysis
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 3
sample_size:
sources:
  - oic/scoring/differentiation.py
  - docs/v4/02-公式与算法规范.md
  - EXT:Anthony Ulwick, Outcome-Driven Innovation
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

1–10 量表。高重要性 + 低满意度 = 高机会分。

## 依据

把「有需求」拆成「有多重要」与「现在满意吗」两个可分别测量的量，比笼统问「有没有需求」可操作得多。

## 边界：什么情况下它不成立

量表分来自受访者主观评分，跨人群、跨品类的可比性有限。

## 代码位置

`oic/scoring/differentiation.py`
