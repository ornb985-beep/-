---
id: K-ACQ-017
title: 取数返回空内容时抛错，不当作「该文件无数据」
domain: acquisition
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 1
sample_size:
sources:
  - oic/sources/fetchers.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`fetch_filing()` 拿到空文本时抛 `FetchError`。

## 依据

空文本会被下游当成「这份申报文件没有相关数据」，从而在覆盖率统计里被记成「查过了，没有」—— 与「没查到」是完全不同的结论。

## 边界：什么情况下它不成立

确实存在文件本身内容极少的情况。那种情况下应当拿到少量文本而非零字节。

## 代码位置

`oic/sources/fetchers.py::fetch_filing`
