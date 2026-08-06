---
id: K-DLV-003
title: 「可预测的结果」写成条件区间 + 反证条件
domain: delivery
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/08-操盘手全流程.md
  - oic/deliver/plan_90day.py
  - oic/scoring/conformal.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

写法固定为：「若假设A且假设B，则 90 天 X 落在 [下界, 上界]（80% 区间）。**反证条件**：14 天内若 Y < Z → 假设A 证伪，立即止损。」

## 依据

**不给伪精确点值。** n 小时点值是编的，标注「置信度低」也救不了 —— 产品里没有人会读那行小字。条件区间同时给出了「什么情况下这个预测不成立」，这才是可执行的。

## 边界：什么情况下它不成立

区间的宽度依赖共形校准样本。校准样本不足时应当拒绝给区间，而不是给一个很宽的区间充数。

## 代码位置

`oic/deliver/plan_90day.py`
