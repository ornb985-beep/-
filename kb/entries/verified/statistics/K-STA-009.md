---
id: K-STA-009
title: ForecastBench：LLM 还没赢过人
domain: statistics
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 4
sample_size:
sources:
  - docs/v4/00-总纲与终局判据.md
  - docs/v4/07-路线图与回退规则.md
  - tests/test_calibration.py
  - EXT:ForecastBench arXiv:2409.19839
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

超级预测者 Brier **0.096**，普通公众 **0.121**，最强 LLM **0.122**。

## 依据

这三个数字钉进了单元测试，防止自我感觉良好。它给出了本系统判断层的天花板：**换模型突破不了普通人水平**。

## 边界：什么情况下它不成立

这是 2024 年的基准。若模型能力有代际跃迁需要重测，但在重测之前不得假设已经突破。

## 代码位置

`tests/test_calibration.py`
