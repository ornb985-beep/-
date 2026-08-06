---
id: K-GOV-017
title: 回退：多 agent 成本失控即退回单 agent
domain: governance
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 1
sample_size:
sources:
  - docs/v4/07-路线图与回退规则.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

**触发条件**：多 agent token >15× 且质量提升 <20%

**动作**：退回单 agent + Chain-of-Verification

触发即执行，不讨论。

## 依据

15× 成本换 20% 质量在任何定价下都不成立

## 边界：什么情况下它不成立

回退规则的价值在于事前写死。事到临头再讨论，讨论的结果一定是「这次情况特殊」。
