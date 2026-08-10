---
id: K-ACQ-005
title: 取数器在代码层做不到伪装浏览器 UA
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

`FetchPolicy` 构造时校验 User-Agent：含 Mozilla/Chrome/Safari/WebKit 等浏览器标识即抛 `DishonestUserAgent`；不含联系邮箱或主页 URL 也抛。

## 依据

UA 伪装留在对方服务器日志里，是**书面证据**。同时 SEC 明文要求 User-Agent 含联系方式，否则限流封禁。可被联系的抓取方在争议中处于完全不同的位置。

## 边界：什么情况下它不成立

这挡不住有人在 SDK 之外自己发请求。它保证的是**这条路径上不存在伪装能力**，而不是全局不可能。

## 代码位置

`oic/sources/http_fetch.py::_assert_honest_user_agent`
