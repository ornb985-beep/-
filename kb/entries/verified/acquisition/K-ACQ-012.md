---
id: K-ACQ-012
title: 超出大小上限时报错，不截断
domain: acquisition
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/sources/http_fetch.py
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

响应体超过 `max_bytes` 时抛 `FetchError`，**不做截断**。

## 依据

截断可能正好切掉含数字的那一段，而下游看不出来。报错是可见的失败，截断是不可见的失败。

## 边界：什么情况下它不成立

确需抓大文件时显式调高 `max_bytes`。默认 8 MiB 对网页足够，对招股书 PDF 可能需要调高。

## 代码位置

`oic/sources/http_fetch.py` 的 `DEFAULT_MAX_BYTES`
