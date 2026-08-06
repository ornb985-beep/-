---
id: K-ACQ-009
title: robots.txt 按 origin 缓存，不是每页都拉
domain: acquisition
type: method
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

每个 origin 的 robots.txt 只取一次，之后走缓存。

## 依据

缓存是必须的而不是优化：每抓一页都去拉一次 robots.txt，会让 robots.txt 本身成为你对该站压力最大的请求 —— 遵守规则的动作反而变成了骚扰。

## 边界：什么情况下它不成立

长时间运行的进程需要考虑缓存过期。当前实现是进程内永久缓存，适合批处理，不适合常驻服务。

## 代码位置

`oic/sources/http_fetch.py::RobotsCache`
