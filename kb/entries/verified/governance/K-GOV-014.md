---
id: K-GOV-014
title: 失效模式8：多 agent 可靠性乘法
domain: governance
type: antipattern
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/07-路线图与回退规则.md
  - oic/config.py
  - docs/v4/12-无限检索与智能体集群.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

5 个 agent 各 95% 准确率串起来 = **77%**（0.95⁵）。人的天性是把好东西全加上，而串联只会更差。

## 依据

`AgentGate` 代码级门禁 + 单元测试断言：`baseline_accuracy is None` 时恒 False。

## 边界：什么情况下它不成立

**可并行**的子任务不受这条约束（实测 +80.8%）。八角度检索就属于可并行那一类。挡的是顺序推理链。

## 代码位置

`oic/config.py::AgentGate`
