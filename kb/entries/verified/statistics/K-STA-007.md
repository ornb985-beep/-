---
id: K-STA-007
title: Murphy 三分解：BS = REL − RES + UNC
domain: statistics
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/calibration/brier.py
  - docs/v4/02-公式与算法规范.md
  - tests/test_calibration.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

Brier 分数可分解为可靠度、分辨度、不确定度三部分。G2 判据 `BS < UNC` 等价于 `RES > REL`。

## 依据

这个分解把「预测好不好」拆成「校准准不准」与「区分得开不开」两个可独立改进的部分。只看 Brier 总分无法知道该改哪一边。

## 边界：什么情况下它不成立

**恒等式只在分箱表示下精确成立。** 实现里用箱内均值 `p_k` 计算 `binned_bs`，并把 `binning_loss = actual_bs − binned_bs` 单独报出来，不藏进残差。

## 代码位置

`oic/calibration/brier.py::murphy_decomposition`
