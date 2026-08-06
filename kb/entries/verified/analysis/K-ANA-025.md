---
id: K-ANA-025
title: 深度调查只查缺口角度，不重复已有字段
domain: analysis
type: method
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 1
sample_size:
sources:
  - oic/research/investigate.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`plan_investigation()` 按当前已有指标，只生成还缺的角度的查询。

## 依据

深度调查的成本应当花在缺口上。已经拿到的字段重复查既费钱又会稀释饱和度判据的信号。

## 边界：什么情况下它不成立

有些字段需要多源交叉验证，那时重复查是必要的。当前实现按「有没有」判断，不按「够不够可靠」判断。

## 代码位置

`oic/research/investigate.py::plan_investigation`
