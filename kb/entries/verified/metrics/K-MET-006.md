---
id: K-MET-006
title: 增速在中文里带符号，比较必须取绝对值
domain: metrics
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/research/audit.py
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`audit` 的量级检查对 `GROWTH_RATE` 族比较**绝对值**。

## 依据

原始实现对 −70 报了误警。原因是增速在中文表述里把方向写在词里（「下滑70%」），数值本身的符号与量级检查的语义不一致。

## 边界：什么情况下它不成立

这条只适用于增速族。对规模、家数等指标，负值本身就是异常，不应取绝对值。

## 代码位置

`oic/research/audit.py::check_magnitude`
