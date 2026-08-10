---
id: K-ACQ-019
title: 中文招股书 PDF 的软换行不能当句末
domain: acquisition
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/sources/filing_parse.py
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

句末判定必须是 `[。；;]` 或**空行**，单个 `\n` 不算。

## 依据

中文招股书 PDF 全是软换行。按单个 `\n` 切句会让「市场规模为\n226.94亿元」丢掉数字 —— 抽取器会认为这句没有数值。

## 边界：什么情况下它不成立

这条针对 PDF 转出的文本。HTML 来源的文本换行语义不同，需要单独处理。

## 代码位置

`oic/sources/filing_parse.py` 的 `_SENTENCE_END`
