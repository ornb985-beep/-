---
id: K-ACQ-020
title: 招股书章节标题必须是短行，否则会在正文里误匹配
domain: acquisition
type: lesson
maturity: verified
status: active
evidence_grade: A
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

章节切分时，标题必须是 ≤40 字的短行（可带编号前缀），不能只靠关键词匹配。

## 依据

只按关键词匹配会在正文中间命中，把文档切碎。真实后果：「行业前五大企业合计市场份额」这句被从中间切断，CR5 数据丢失。

## 边界：什么情况下它不成立

遇到超长标题或标题与正文同行的排版，这条规则会漏切。漏切的后果是章节过大，比切碎安全。

## 代码位置

`oic/sources/filing_parse.py`
