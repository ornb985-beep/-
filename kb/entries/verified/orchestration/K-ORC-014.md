---
id: K-ORC-014
title: provider_code 缺省带 UNFILED- 前缀
domain: orchestration
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
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

未填算法备案号时，默认值是 `UNFILED-<APP>`，且会写进导出元数据。

## 依据

一个看起来像真编码的默认值会被原样带上线；带 `UNFILED-` 的不会。这是「让错误变吵闹」的一般原则在标识层的应用。

## 边界：什么情况下它不成立

它不阻止上线 —— 开发期需要能跑起来。它只保证这件事**藏不住**。

## 代码位置

`oic/sdk.py::UNFILED_PREFIX`
