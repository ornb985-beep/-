---
id: K-MET-011
title: 单位与币种必须先归一再比较
domain: metrics
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/research/units.py
  - tests/test_research.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`parse_quantity` / `parse_percent` 处理中文数量级词（万/亿）与币种，归一后才允许进入计算。

## 依据

「226.94亿元」与「22694000000元」是同一个数，但字符串比较、甚至朴素的数值解析都会把它们当成不同的量级。

## 边界：什么情况下它不成立

跨币种比较需要汇率，而汇率有时点。当前实现要求显式指定币种，不做自动换算 —— 换算需要一个 as-of 汇率源。

## 代码位置

`oic/research/units.py`
