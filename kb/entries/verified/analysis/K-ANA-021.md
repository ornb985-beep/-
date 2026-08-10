---
id: K-ANA-021
title: 八角度调查矩阵：缺哪个角度，字段就永远是空的
domain: analysis
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size: 7
sources:
  - oic/research/investigate.py
  - data/research/SATURATION.md
  - docs/v4/12-无限检索与智能体集群.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

demand_size / supply_entry / supply_exit / concentration / capital / profitability / channel / regulation。刻意穷举而非精选。

## 依据

实测（盲盒/潮玩，同一品类）：1 次查询 → 2 条事实；**7 次多角度 → 17 条事实**（含企业存量 2600、新增序列 300→1470、CR5 24%、龙头份额 12%、市场规模 478亿、融资 35 起）。**供给侧和集中度数据一直在互联网上，缺的是查询角度。**

## 边界：什么情况下它不成立

多查一次的成本远低于一个永久性的数据缺口，但角度本身是人定的 —— 没想到的角度仍然是盲区。

## 代码位置

`oic/research/investigate.py::build_query_matrix`
