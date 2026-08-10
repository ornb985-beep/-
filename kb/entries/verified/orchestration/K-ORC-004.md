---
id: K-ORC-004
title: 四级漏斗：不设限粗筛 → 零成本去重 → 分流 → 贵通道精查
domain: orchestration
type: method
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/12-无限检索与智能体集群.md
  - oic/pipeline/budget.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

L1 不设限全量收集 → L2 查重/归一/信源折叠（**纯程序，零成本**）→ L3 按分数分流 → L4 八角度深度调查（贵模型）。

## 依据

「不限成本」和「分层降本」不冲突，恰恰相反：不限成本让第一级可以真的放开，前提是后面几级把量收住。

## 边界：什么情况下它不成立

L2 必须是零成本的确定性程序。把去重交给 LLM 既贵又不可复现 —— 同一批输入两次跑出不同的去重结果，后面所有统计都失去意义。

## 代码位置

`oic/pipeline/budget.py::select_for_escalation`
