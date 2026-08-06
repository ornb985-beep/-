---
id: K-MET-004
title: 市占率不是市场规模
domain: metrics
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/research/metrics.py
  - oic/sources/filing_parse.py
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

招股书抽取时曾把市占率（百分数）标成市场规模（金额），修法是新增 `Family.MARKET_SHARE` 并把 CR5 与自身份额分开。

## 依据

份额混进规模会直接毁掉集中度计算 —— HHI 的输入变成了金额，输出是个无意义的大数。

## 边界：什么情况下它不成立

CR5（前五大合计）与单家自身份额是不同 Scope，也不能互相替代。

## 代码位置

`oic/research/metrics.py::Family.MARKET_SHARE`
