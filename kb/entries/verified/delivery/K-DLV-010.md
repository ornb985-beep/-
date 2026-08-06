---
id: K-DLV-010
title: top3 而不是全量排序
domain: delivery
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 2
sample_size:
sources:
  - oic/deliver/business_plan.py
  - docs/v4/08-操盘手全流程.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

交付物只出 top3 商业计划书。

## 依据

全量排序的尾部本来就是噪声（尤其在 G1 未过时）。输出 top3 是对自身分辨率的诚实表达。

## 边界：什么情况下它不成立

top3 的选择依赖排序有效性，而排序有效性尚未通过 G2。当前 top3 应当被当作「值得人工细看的三个」，不是「最好的三个」。

## 代码位置

`oic/deliver/business_plan.py`
