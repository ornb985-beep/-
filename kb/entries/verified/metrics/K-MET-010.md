---
id: K-MET-010
title: audit 报 ERROR 的品类，下游拒绝使用
domain: metrics
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/research/audit.py
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

`assert_data_usable()` 在有任一 ERROR 时抛 `DataRejected`，而不是「警告后继续」。

## 依据

**错数据上建的一切结论都是错的。**警告在实践中等于没有 —— 赶进度时没人会为一条黄色提示停下来。

## 边界：什么情况下它不成立

WARN 级别的发现不阻断，只提示。ERROR 与 WARN 的划分决定了这道闸的松紧，需要随实践调整。

## 代码位置

`oic/sdk.py::OIC.assert_data_usable`
