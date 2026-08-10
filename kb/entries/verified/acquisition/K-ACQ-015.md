---
id: K-ACQ-015
title: 订阅源解析不出条目时抛错，不返回空列表
domain: acquisition
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/sources/rss.py
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`parse_feed()` 在内容为空、XML 非法、或解析出 0 条时一律抛 `FeedError`。

## 依据

返回空列表会被上层读成「今天没有新内容」—— 那是一个**错误结论**，不是数据。而错误结论会安静地进入统计。

## 边界：什么情况下它不成立

确实存在「今天真的没有更新」的情况。那时 feed 里仍有历史条目，`filter_by_date` 会过滤成空 —— **过滤成空**和**解析失败**是两回事，代码里分得很清楚。

## 代码位置

`oic/sources/rss.py::FeedError`
