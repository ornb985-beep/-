---
id: K-ORC-002
title: 铁律2：没有实测基线，不准扩多智能体
domain: orchestration
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/00-总纲与终局判据.md
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

`AgentGate.multi_agent_allowed()` 在 `baseline_accuracy is None` 时**恒返回 False**。先测单 agent 基线，才谈得上扩集群。

## 依据

Google + MIT 的 45% 规则：单 agent 准确率超过约 45% 后，加 agent 收益递减甚至转负。可并行任务实测 +80.8%；顺序推理任务实测倒退 39–70%。5 个 agent 各 95% 串联 = 77%。

## 边界：什么情况下它不成立

这条挡的是「顺序推理链上堆 agent」。可拆成独立子任务的场景（如八角度检索）不受限制，那属于 +80.8% 那一类。

## 代码位置

`oic/config.py::AgentGate.multi_agent_allowed`
