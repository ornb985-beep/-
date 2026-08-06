---
id: K-EVD-008
title: URL 掩码必须等长
domain: evidence
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/compliance/securities_guard.py
  - tests/test_compliance.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`mask_urls()` 用等长的全角空格替换 URL，而不是短占位符。

## 依据

违规位置 `position` 必须仍然指向**原文的正确偏移**，否则人工复核时按位置去原文找会对不上。

## 边界：什么情况下它不成立

等长替换让被掩码区域在视觉上是空白。这只影响调试输出，不影响判定。

## 代码位置

`oic/compliance/securities_guard.py::mask_urls`
