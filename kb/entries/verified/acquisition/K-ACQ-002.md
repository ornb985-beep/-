---
id: K-ACQ-002
title: SCRAPING 类源永不放行，法务放行也不行
domain: acquisition
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 4
sample_size:
sources:
  - oic/compliance/provenance.py
  - db/schema.sql
  - docs/v4/06-合规内核.md
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`access_method == SCRAPING` 的源，**无论 legal_status 填什么都不会出现在 `allowed_keys()` 里**。代码闸 + 数据库 CHECK 双保险。

## 依据

《反不正当竞争法》(2025) 第13条第3款禁止「以避开或者破坏技术管理措施等方式获取他人合法持有的数据」。德恒统计 2011–2022 年 12 起「爬虫+不正当竞争」案，爬取方胜诉率 **<16.67%**。

## 边界：什么情况下它不成立

这条挡的是绕过技术措施的抓取。站点主动提供的 RSS、开放 API、robots 允许的页面都不属于此列，走正常放行流程。

## 代码位置

`oic/compliance/provenance.py` 的 `scraping_never_cleared`
