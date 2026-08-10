---
id: K-EVD-009
title: 证据分 A/B/C/D 四级
domain: evidence
type: method
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/research/dossier.py
  - docs/v4/02-公式与算法规范.md
  - oic/kb/schema.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

A 法定披露 / 政府统计 / 本仓库通过的测试；B 行业协会 / 可信媒体 / 一级数据商；C 二手转引；D 单一自媒体 / 无可核查出处。

## 依据

分级让「有出处」这件事可比较。没有分级时，一条微博和一份年报在系统里长得一样。

## 边界：什么情况下它不成立

分级是对**来源类型**的判断，不是对**内容正确性**的判断。A 级来源也会出错（招股书有自利披露倾向）。

## 代码位置

`oic/kb/schema.py::Grade`
