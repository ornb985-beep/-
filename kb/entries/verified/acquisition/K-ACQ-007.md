---
id: K-ACQ-007
title: robots.txt 不可达时视为完全禁止
domain: acquisition
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/sources/http_fetch.py
  - tests/test_sources.py
  - EXT:RFC 9309 §2.3.1.4
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

4xx（Unavailable）→ 视为无限制可以抓；5xx（Unreachable）或网络错误 → **视为完全禁止**。

## 依据

RFC 9309 §2.3.1.4 的明文规定。**「拿不到规则」不等于「没有规则」。**异常捕获刻意写得很宽（`except Exception`）—— 漏掉一种异常类型就等于在那种情况下默认放行。

## 边界：什么情况下它不成立

这会让偶发网络抖动导致整站暂时不可抓。这个代价是刻意付的：宁可少抓，不可误闯。

## 代码位置

`oic/sources/http_fetch.py::RobotsCache.decide`
