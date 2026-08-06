---
id: K-EVD-011
title: 只有预测值的数据一律排除
domain: evidence
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - data/research/PROTOCOL.md
  - data/research/FINDINGS.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

结局数据若只查到预测值（如「预计 2028 年 CAGR 17.54%」），该品类标 null 而非采用预测值。

## 依据

**用预测当结局等于拿模型验证模型。**功能性护肤这个品类就是因此被排除的。

## 边界：什么情况下它不成立

被排除的品类**仍然计入分母**（规则 E2），否则会制造幸存者偏差 —— 只统计查得到结局的品类会系统性高估。
