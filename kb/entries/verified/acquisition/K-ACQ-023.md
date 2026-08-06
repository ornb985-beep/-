---
id: K-ACQ-023
title: 微博热搜与知乎热榜：登记为 SCRAPING，永不放行
domain: acquisition
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/compliance/provenance.py
  - docs/v4/09-方案融合与缺口.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

这两个源在登记表里是 `SCRAPING`，因此 `allowed_keys()` 永远不含它们。

## 依据

用户提供的抓取现状是「近期连续抓取失败，反爬，待修」。在反不正当竞争法第13条第3款下，这是停止信号。

## 边界：什么情况下它不成立

它们的热度信息确实有价值。替代路径是官方开放平台（若有）或第三方合规聚合，而不是绕过。

## 代码位置

`oic/compliance/provenance.py`
