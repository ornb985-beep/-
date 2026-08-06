---
id: K-STA-013
title: 共形预测给带覆盖保证的区间
domain: statistics
type: method
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/scoring/conformal.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

用共形方法给出区间预测，在交换性假设下有有限样本覆盖保证。

## 依据

点预测在小样本下是编的。共形区间的覆盖保证不依赖分布假设，是小样本下少数还站得住的工具。

## 边界：什么情况下它不成立

校准样本不足时**拒绝输出**（返回 NaN 区间）而非给个宽区间 —— 宽到无意义的区间会被当成有信息。

## 代码位置

`oic/scoring/conformal.py::conformal_interval`
