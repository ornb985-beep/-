---
id: K-MET-002
title: 存量与流量混淆会得出「新增大于存量」
domain: metrics
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/research/metrics.py
  - oic/research/audit.py
  - tests/test_research.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`Measure.STOCK`（时点存量）与 `Measure.FLOW`（期间流量）在代码层是不同指标，不可合并。`audit.check_stock_flow` 会抓出违反。

## 依据

新增注册数（流量）大于存续企业数（存量）在逻辑上不可能。这类错误在混用口径时非常容易发生，且看上去像个合理的大数字。

## 边界：什么情况下它不成立

累计流量与存量增量在理论上应当接近，但因注销、迁移等因素不会完全相等。检查用的是容差而非严格相等。

## 代码位置

`oic/research/audit.py::check_stock_flow`
