---
id: K-GOV-012
title: 失效模式6：数据源合法性可能整体崩塌
domain: governance
type: antipattern
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/07-路线图与回退规则.md
  - oic/compliance/provenance.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

若二手转卖不可抓 + 蝉妈妈/企查查按量太贵，则「后悔信号 + 剪刀差」两大差异化**同时消失**。

## 依据

缓解：Wave 0 必须先跑完源登记表再写任何采集代码。这是唯一能在花钱之前测掉的致命风险。

## 边界：什么情况下它不成立

这条已经部分兑现 —— 供给侧数据实测覆盖只有 5/30，剪刀差目前确实悬空。

## 代码位置

`oic/compliance/provenance.py::Registry`
