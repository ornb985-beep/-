---
id: K-DLV-005
title: 资源规划给三技能模型缺口，不给岗位名称
domain: delivery
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 2
sample_size:
sources:
  - oic/deliver/resourcing.py
  - docs/v4/08-操盘手全流程.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

输出「缺哪类技能」而不是「招一个运营」。

## 依据

岗位名称在不同公司含义差别极大。技能缺口可以由一个人补也可以由外包补，决策空间更大。

## 边界：什么情况下它不成立

三技能模型本身是简化。复杂业务的技能维度远不止三个。

## 代码位置

`oic/deliver/resourcing.py::build_resource_plan`
