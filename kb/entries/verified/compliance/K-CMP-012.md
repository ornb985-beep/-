---
id: K-CMP-012
title: PIPL：处理个人信息需要 PIPIA
domain: compliance
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/compliance/provenance.py
  - docs/v4/06-合规内核.md
  - db/schema.sql
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

登记表里 `handles_personal_info` / `handles_sensitive_pi` 为真的源，必须 `pipia_completed` 才可放行。

## 依据

个人信息保护影响评估是法定前置程序，不是可选项。把它做成放行条件，比写在流程文档里可靠。

## 边界：什么情况下它不成立

PIPIA 的实质内容由法务完成，代码只能检查「有没有做」。

## 代码位置

`oic/compliance/provenance.py::SourceRecord`
