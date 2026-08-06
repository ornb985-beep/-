---
id: K-ACQ-006
title: 没有忽略 robots.txt 的开关
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

`FetchPolicy` 里不存在 `ignore_robots` / `bypass_robots` / `force` 字段，并有一条测试断言这些字段名不存在。

## 依据

「默认关闭」的开关一定会被打开。**不存在**才是真的关闭。

## 边界：什么情况下它不成立

robots.txt 只表达站点意愿，不是法律本身。但遵守它是「善意抓取」最容易举证的一条。

## 代码位置

`oic/sources/http_fetch.py::FetchPolicy`
