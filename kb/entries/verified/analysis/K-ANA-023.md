---
id: K-ANA-023
title: 信息饱和度：连续 3 次边际产出 <5% 即可停
domain: analysis
type: criterion
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

`assess_saturation()` 把「信息够不够」从感觉变成判据。

## 依据

实测（即时零售，7 次查询）：产出 2、4、3、0、2、3、3 —— **未饱和**。说明多角度调查的边际价值仍为正，该继续查。

## 边界：什么情况下它不成立

窗口 3 与阈值 5% 都是 PRIOR。且饱和只说明「这条路挖完了」，不说明「信息足够做决策了」。

## 代码位置

`oic/research/investigate.py::assess_saturation`
