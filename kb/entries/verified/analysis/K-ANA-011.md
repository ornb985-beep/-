---
id: K-ANA-011
title: Schwartz 成熟度按同类企业数自动定级
domain: analysis
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 3
sample_size:
sources:
  - oic/scoring/supply.py
  - docs/v4/02-公式与算法规范.md
  - EXT:Eugene Schwartz《Breakthrough Advertising》
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

L1 ≤10 家、L2 ≤50、L3 ≤200、L4 >200。级别决定文案策略。

## 依据

市场成熟度决定「该说什么」：L1 说清楚是什么，L4 必须说清楚凭什么是你。用企业数做代理是因为它可机械获取。

## 边界：什么情况下它不成立

企业数只是成熟度的**代理变量**，不是定义。同样 50 家企业，有的市场很成熟有的还在早期。分档边界是 PRIOR。

## 代码位置

`oic/scoring/supply.py`
