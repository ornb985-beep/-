---
id: K-DLV-001
title: BP 里每条论证都挂着可追溯证据
domain: delivery
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/deliver/business_plan.py
  - docs/v4/08-操盘手全流程.md
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

商业计划书的每条依据都带 source URL + 指标口径 + 原文 span。

## 依据

「有理有据」如果不能点开看到原文，读者就只能选择相信。可追溯把「相信我」换成「你自己看」。

## 边界：什么情况下它不成立

可追溯不等于正确。原文本身可能错，来源可能有自利倾向 —— 那由证据分级与双源锚定处理。

## 代码位置

`oic/deliver/business_plan.py::build_business_plans`
