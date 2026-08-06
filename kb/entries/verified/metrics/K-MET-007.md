---
id: K-MET-007
title: 增速自洽冲突时两个来源都不用
domain: metrics
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/research/audit.py
  - data/research/FINDINGS.md
  - tests/test_research.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

报告的增速与由两年存量推算的增速差异过大时，`check_growth_consistency` 报 ERROR，**两个来源都不采用**。

## 依据

真实案例：咖啡 2021 新增 2.6 万家 → 2022 新增 1.9 万家是 **−26.9%**，而来源自称「同比增长 +26.6%」。两者不可能同真，我无法判定谁对。**代码强制两个都丢弃，不给人工挑一个好看的机会。**

## 边界：什么情况下它不成立

这会损失可用数据（咖啡的供给侧因此空缺）。损失一条数据的代价，远小于采用了错误数据的代价。

## 代码位置

`oic/research/audit.py::check_growth_consistency`
