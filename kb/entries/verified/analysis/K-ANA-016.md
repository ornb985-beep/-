---
id: K-ANA-016
title: HHI 衡量竞争格局集中度
domain: analysis
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/scoring/concentration.py
  - docs/v4/02-公式与算法规范.md
  - tests/test_scoring.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

HHI = Σ(份额百分数)²。>1800 视为高度集中（与 R4 联动）。

## 依据

集中度决定了「还有没有位置」。HHI 比 CR5 更敏感于份额分布的不均。

## 边界：什么情况下它不成立

输入必须是**份额**不是规模（曾踩过这个坑）。且份额数据本身在公开渠道极难获取 —— 这是招股书的价值所在。

## 代码位置

`oic/scoring/concentration.py`
