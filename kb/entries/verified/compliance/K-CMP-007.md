---
id: K-CMP-007
title: 关键豁免：纯信息汇总不属于荐股软件
domain: compliance
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/compliance/securities_guard.py
  - docs/v4/06-合规内核.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

仅有证券信息汇总或历史数据统计、不具备荐股四功能的软件，**不属于**荐股软件。

## 依据

这条豁免是本系统合法性的基础：纯商业/市场/创业机会分析（行业趋势、商业模式、市场规模）**不需要**证监会牌照。

## 边界：什么情况下它不成立

豁免的前提是四项功能一个都不沾。S1–S4 的存在就是为了守住这个前提。

## 代码位置

`oic/compliance/securities_guard.py`
