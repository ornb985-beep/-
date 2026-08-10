---
id: K-STA-002
title: Bootstrap 给区间，不给点值
domain: statistics
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/stats/resample.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

相关系数等统计量报告 Bootstrap 置信区间而非单一点估计。

## 依据

本项目实测的区间宽到必须看见才不会被误导：cohort1 的 ρ 区间是 [−0.907, +0.683]，横跨整个可能范围。只报 −0.289 这个点值会让人以为发现了什么。

## 边界：什么情况下它不成立

小样本 Bootstrap 本身也不可靠 —— 它只能反映样本内的变异，不能反映样本不代表总体的风险。

## 代码位置

`oic/stats/resample.py::bootstrap_ci`
