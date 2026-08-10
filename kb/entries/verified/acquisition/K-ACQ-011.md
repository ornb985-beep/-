---
id: K-ACQ-011
title: 解码失败抛错，绝不用 errors='replace'
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

按 声明编码 → meta charset → utf-8 → gb18030 → big5 顺序尝试严格解码，全失败则抛 `DecodeError`。

## 依据

`errors='replace'` 会把「226.94亿元」变成「226.94�元」而不报错，下游只会看到少了一个字。**数量级错误就是这么产生的。**解码顺序也有讲究：gb18030 几乎能解出任意字节序列，放在 utf-8 之后才不会抢先产出一堆不报错的乱码。

## 边界：什么情况下它不成立

对确实混合编码的页面，这条会导致整页取不到。那是正确行为 —— 半页正确半页乱码的文本无法用于证据。

## 代码位置

`oic/sources/http_fetch.py::decode_body`
