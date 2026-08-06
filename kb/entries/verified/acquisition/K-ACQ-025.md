---
id: K-ACQ-025
title: 国家统计局是 A 级来源
domain: acquisition
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/compliance/provenance.py
  - docs/v4/09-方案融合与缺口.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

政府公开宏观消费数据，登记为 A 级。

## 依据

政府统计有法定发布程序与责任主体，是公开渠道里等级最高的一类。

## 边界：什么情况下它不成立

宏观数据的口径通常是全国、全品类，与具体商机所需的细分品类口径差距很大 —— 跨 Scope 不得直接合并。

## 代码位置

`oic/compliance/provenance.py`
