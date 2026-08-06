---
id: K-ACQ-004
title: 403/429 后不重试、不换 UA、不换 IP
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

收到 401/402/403/407/429/451 立即抛 `AccessRefused`，**只发出过一次请求**。

## 依据

换个身份再来一次，法律性质从「被拒绝」变成「规避技术管理措施」。有一条测试断言请求计数恰好为 1 —— 「不重试」这条纪律只有靠计数才测得出来。

## 边界：什么情况下它不成立

降低频率后重新尝试是允许的，那是遵守而非规避。但那应当是人的决策，不是取数器的自动行为。

## 代码位置

`oic/sources/http_fetch.py::HttpFetcher.fetch`
