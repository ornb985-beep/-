---
id: K-EVD-002
title: 数值展开必须处理中文单位
domain: evidence
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/evidence/grounding.py
  - tests/test_evidence.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`expand_numbers()` 把「3万单」展开成 (3.0, 30000.0)，这样模型写 30000 而原文写 3万 时仍能匹配上。

## 依据

不做展开会导致大量正确抽取被误判为幻觉，从而逼着人放宽校验 —— 那才是真正的风险。

## 边界：什么情况下它不成立

展开也意味着「3万」和「3」都能匹配 30000 与 3。这个宽松是刻意的，代价由量级检查（>10×）兜底。

## 代码位置

`oic/evidence/grounding.py::expand_numbers`
