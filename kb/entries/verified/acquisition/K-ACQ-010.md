---
id: K-ACQ-010
title: 条件请求省对方流量也省自己的
domain: acquisition
type: method
maturity: implemented
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

有缓存时自动带 `If-None-Match` / `If-Modified-Since`；收到 304 直接用本地内容。

## 依据

对榜单类高频源，条件请求能把绝大部分请求变成 304，既降低对方负载也降低自己的带宽成本。

## 边界：什么情况下它不成立

304 但本地无缓存内容时**抛错而非返回空** —— 缓存状态不一致是真问题，静默返回空会被下游读成「今天没内容」。

## 代码位置

`oic/sources/http_fetch.py::HttpFetcher.fetch`
