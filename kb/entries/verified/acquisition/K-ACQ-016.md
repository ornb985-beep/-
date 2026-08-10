---
id: K-ACQ-016
title: 日期解析不出来就留空，绝不填今天
domain: acquisition
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/sources/rss.py
  - oic/research/asof.py
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`_normalize_date()` 认不出的日期返回空串；`filter_by_date()` **一律排除无日期条目**。

## 依据

一个猜出来的日期会直接制造前视偏差 —— 把今天的内容当成 as-of 日就有的信息，回测结论全废。

## 边界：什么情况下它不成立

这会漏掉一些实际上有效但日期格式罕见的条目。漏掉可用数据的代价，远小于污染时间闸的代价。

## 代码位置

`oic/sources/rss.py::filter_by_date`
