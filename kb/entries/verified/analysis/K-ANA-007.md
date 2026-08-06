---
id: K-ANA-007
title: 红线 R5：数据不可信
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

**触发条件**：刷单风险分 > 60 → 排序分归零。

## 依据

底层数据不可信时，任何分析都是在错的数字上做的

## 边界：什么情况下它不成立

阈值为 PRIOR，未经真实数据校准，界面必须显示「未校准」。

## 代码位置

`oic/scoring/redlines.py`
