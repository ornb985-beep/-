---
id: K-ANA-004
title: 红线 R2：绞肉机
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

**触发条件**：剪刀差 M ≤ −30% 且死亡率 > 15% → 排序分归零。

## 依据

需求在退、供给还在涌入 —— 这是最典型的把钱亏光的结构

## 边界：什么情况下它不成立

阈值为 PRIOR，未经真实数据校准，界面必须显示「未校准」。

## 代码位置

`oic/scoring/redlines.py`
