---
id: K-ANA-012
title: 切换势能 = (推力+拉力) − (焦虑+惯性)
domain: analysis
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 3
sample_size:
sources:
  - oic/scoring/switching.py
  - docs/v4/02-公式与算法规范.md
  - EXT:JTBD 四力模型
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

四力各 0–100，势能 ≤0 触发 R3 红线。

## 依据

痛点存在不等于会换。JTBD 四力把「为什么不换」显式建模，而不是假设有痛点就有生意。

## 边界：什么情况下它不成立

四力的打分来自 LLM，是判断不是测量。系数与阈值均为 PRIOR。

## 代码位置

`oic/scoring/switching.py`
