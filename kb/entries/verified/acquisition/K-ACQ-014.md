---
id: K-ACQ-014
title: RSS 在合规上优于抓页面
domain: acquisition
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/sources/rss.py
  - docs/v4/10-嵌入你的App.md
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

RSS/Atom 是**发布方主动提供的订阅源**，属于「被邀请读取」而非「绕过措施」。36氪 / 虎嗅 / 亿欧 这类源应优先走 RSS。

## 依据

同样的内容，通过 RSS 获取与通过抓页面获取，法律性质不同。前者是发布方的意思表示，后者需要另行论证。

## 边界：什么情况下它不成立

RSS 通常只给摘要与最近若干条，拿不到全文与历史。需要全文时仍要回到页面，那时 robots 与限速规则照常适用。

## 代码位置

`oic/sources/rss.py::parse_feed`
