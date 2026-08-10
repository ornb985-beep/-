---
id: K-STA-012
title: 已解析结局 <30 时 Kelly 与概率一律拒绝输出
domain: statistics
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 4
sample_size:
sources:
  - oic/scoring/kelly.py
  - oic/config.py
  - oic/sdk.py
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`MIN_SAMPLES_FOR_CALIBRATION = 30`。低于此值，`position_size` 返回 refused，`predict_probability` 抛 `NotCalibrated`。

## 依据

<30~50 样本时 REL/ECE 的方差极大，算出来的校准指标本身不可信。**产品里没有人会读「置信度低」那行小字，而一个编出来的 42% 会被当成 42% 用。**

## 边界：什么情况下它不成立

30 这个数是常用经验门槛，不是从本项目数据推出的。更严格的做法是按目标精度反推所需样本量。

## 代码位置

`oic/config.py` 的 `MIN_SAMPLES_FOR_CALIBRATION`
