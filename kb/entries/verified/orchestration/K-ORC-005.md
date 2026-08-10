---
id: K-ORC-005
title: 低成本 AI 只能做归类，不能替代精查
domain: orchestration
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/12-无限检索与智能体集群.md
  - oic/evidence/grounding.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

低成本模型在**判断**上不可靠，在**归类**上够用。它的位置是 L2/L3 的辅助（打粗标签、聚类），不是 L4 的替代。

## 依据

L4 的输出会进商业计划书，而 BP 里每个数字都要过字符级 grounding。用便宜模型省下的钱，会在一次 100× 单位错上全赔回去 —— 这不是假设，是本项目真实犯过的错。

## 边界：什么情况下它不成立

如果某天低成本模型在本任务上的实测准确率追平贵模型，这条应当重测。但**要先测**，不能因为「听说变强了」就换。

## 代码位置

`oic/evidence/grounding.py::verify_claim`
