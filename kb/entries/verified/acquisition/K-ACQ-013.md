---
id: K-ACQ-013
title: HTML 只去标签，不做正文抽取
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

`html_to_text()` 删除 script/style 与标签、还原实体，**不跑 Readability 那类正文抽取算法**。

## 依据

抽取算法会丢段落，而丢掉的可能正是含数字的那一段。宁可留噪声 —— 噪声下游看得见，缺失看不见。

## 边界：什么情况下它不成立

代价是文本里混着导航、广告、备案号。这些噪声由后续的 grounding 与 audit 过滤，而不是在取数阶段猜。

## 代码位置

`oic/sources/http_fetch.py::html_to_text`
