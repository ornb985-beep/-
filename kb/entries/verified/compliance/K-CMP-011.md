---
id: K-CMP-011
title: provider_code 应填真实算法备案号
domain: compliance
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/compliance/ai_labeling.py
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

GB 45438-2025 的隐式标识要求真实的服务提供者编码。缺省值带 `UNFILED-` 前缀并写进元数据。

## 依据

开发期需要能跑起来，所以不强制阻断；但缺省值必须**看起来就是缺省值**，否则会被原样带上线。

## 边界：什么情况下它不成立

`capabilities()` 里 `aigc_filing` 一项会显示未就绪。上线前必须替换。

## 代码位置

`oic/sdk.py::UNFILED_PREFIX`
