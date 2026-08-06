---
id: K-ANA-010
title: 剪刀差 M = 需求增速 − 供给增速
domain: analysis
type: method
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/scoring/supply.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

单位是百分点。分档：M≥+30 强机会(1.3)、M≥+10 窗口开着(1.1)、M≥−10 均衡(1.0)、M<−10 拥挤(0.7)。

## 依据

「需求在涨」到处都是，「需求涨得比供给快」才是窗口。这是本系统最大的差异化设计。

## 边界：什么情况下它不成立

**全部分档边界与系数都是 PRIOR。**且实测供给侧覆盖只有 5/30，这个指标目前大部分时候算不出来。

## 代码位置

`oic/scoring/supply.py`
