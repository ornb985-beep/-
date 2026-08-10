---
id: K-ANA-019
title: 变化率评分：趋势 60 + 幅度 20 + 形状 20
domain: analysis
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/research/velocity.py
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`velocity_score = 趋势基分(UP=60) + 幅度分(≤20) + 形状分(≤20)`。

## 依据

初版给 UP 基分 100，导致 +20% 和 +100% 都是满分，**排序退化成指纹字母序** —— 一个看起来在工作、实际已失效的评分。留出幅度与形状的空间后才恢复区分度。

## 边界：什么情况下它不成立

这类「饱和导致排序失效」的 bug 不会报错，只会让结果看起来随机。需要专门检查分数分布才能发现。

## 代码位置

`oic/research/velocity.py::velocity_score`
