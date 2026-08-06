---
id: K-CMP-010
title: 内容编号必须确定性
domain: compliance
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/compliance/ai_labeling.py
  - docs/v4/06-合规内核.md
  - tests/test_compliance.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`content_id()` 对正文与提供者做确定性摘要，同一份内容重新导出得到同一编号。

## 依据

编号不确定的话，审计时无法把线上内容与存档对上 —— 标识就失去了追溯价值。

## 边界：什么情况下它不成立

正文改一个字编号就变。这是正确行为：改过的内容就是另一份内容。

## 代码位置

`oic/compliance/ai_labeling.py::content_id`
