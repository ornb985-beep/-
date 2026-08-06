---
id: K-STA-008
title: 分箱损失必须单独报，不藏进残差
domain: statistics
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/calibration/brier.py
  - docs/v4/11-全景总纲.md
  - tests/test_calibration.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`binning_loss = actual_bs − binned_bs` 作为独立字段输出。

## 依据

初版实现的 Murphy 恒等式残差是 1.6e-3，看起来像浮点误差。实际上恒等式只在分箱表示下精确成立，那 1.6e-3 是分箱造成的真实信息损失。把它当浮点误差吞掉，就掩盖了「分箱粒度选得对不对」这个真问题。

## 边界：什么情况下它不成立

分箱数是可调参数。箱越多分箱损失越小但每箱样本越少，REL 的估计方差越大。这是个需要按样本量权衡的选择。

## 代码位置

`oic/calibration/brier.py` 的 `binning_loss`
