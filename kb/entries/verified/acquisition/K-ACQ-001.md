---
id: K-ACQ-001
title: 数据源白名单是采集层的唯一入口
domain: acquisition
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/compliance/provenance.py
  - docs/v4/06-合规内核.md
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

任何取数动作前必须 `registry.assert_source_allowed(key)`。**没有例外通道。**

## 依据

白名单默认全空 —— 在为每个源填上 ToS 链接、法务结论、复核日期之前，采集层本就不该能跑。这个默认值是正确的起点，不是未完成状态。

## 边界：什么情况下它不成立

白名单管的是「能不能取」，不管「取回来对不对」。数据质量由证据层与纠错层负责。

## 代码位置

`oic/compliance/provenance.py::Registry.assert_source_allowed`
