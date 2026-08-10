---
id: K-ACQ-008
title: 站点声明的 Crawl-delay 只会让间隔变长
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

实际等待间隔 = `max(本方配置, 站点 Crawl-delay)`。站点说慢点就慢点，本方配置不用来覆盖它。

## 依据

限速的意义在于不给对方造成压力。用自己的配置去覆盖对方的声明，就把限速变成了自我安慰。

## 边界：什么情况下它不成立

遇到 `Crawl-delay: 3600` 的正确回应是一小时抓一页或者不抓，不是加个开关把它关掉。

## 代码位置

`oic/sources/http_fetch.py::RateLimiter.wait`
