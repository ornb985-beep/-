---
id: K-MET-001
title: 指标身份 = Family × Scope × Measure 三要素
domain: metrics
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/research/metrics.py
  - docs/v4/03-数据契约与Schema.md
  - tests/test_research.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

四要素（含年份）全等才允许合并。任意一维不同即视为不同指标。

## 依据

不做这个区分会得出荒谬结论。本项目实测拦下过：核心市场规模与带动市场规模被当成同一指标平均。

## 边界：什么情况下它不成立

三轴会让指标数量膨胀，很多格子是空的。空格子是**盲区地图**的输入，不是缺陷。

## 代码位置

`oic/research/metrics.py::MetricKey`
