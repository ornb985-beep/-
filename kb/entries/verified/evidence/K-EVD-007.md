---
id: K-EVD-007
title: 证券闸误杀过真实 URL —— 且我当时声称过 0 误杀
domain: evidence
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/compliance/securities_guard.py
  - docs/v4/11-全景总纲.md
  - tests/test_compliance.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

新浪链接 `doc-ikyamrmz7882579.shtml` 里，`882579` 后跟 `.sh`（来自 `.shtml`），被判成 A 股代码，整份报告被阻断。

## 依据

我当时声称「0 误杀」，但只在**精选散文**上测过。商业计划书引用的每条证据都带 URL —— 这个误杀会让几乎每份报告都被拦。修法：边界断言 + `mask_urls()` 预处理。那条真实 URL 现在是回归用例。

## 边界：什么情况下它不成立

**误杀正是历史上导致团队关掉整道闸的主因。**所以合规闸的误杀率和漏杀率同等重要，不能只测漏杀。

## 代码位置

`oic/compliance/securities_guard.py::mask_urls`
