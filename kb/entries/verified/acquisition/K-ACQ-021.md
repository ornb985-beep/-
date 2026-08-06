---
id: K-ACQ-021
title: PDF 的 CID 字体需要 ToUnicode CMap 才能正确提取
domain: acquisition
type: lesson
maturity: verified
status: active
evidence_grade: B
n_independent_sources: 1
sample_size:
sources:
  - oic/sources/filing_parse.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

中文 PDF 常用 CID 编码字体，直接取字节会得到乱码，必须解析 ToUnicode CMap 做映射。

## 依据

本项目实测：不解析 CMap 时提取出的是无意义字符序列，而不是明显的报错 —— 这类失败很容易被当成「这份文件没内容」。

## 边界：什么情况下它不成立

没有嵌入 ToUnicode 的 PDF 无法用这条路恢复，需要 OCR 或换来源。
