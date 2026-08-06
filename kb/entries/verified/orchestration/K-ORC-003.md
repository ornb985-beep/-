---
id: K-ORC-003
title: 铁律3：挑战者必须有独立上下文
domain: orchestration
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/00-总纲与终局判据.md
  - docs/v4/04-Agent契约.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

验证 agent **不能看到原答案**。Chain-of-Verification 必须用**分解式**（factored）：验证问题在独立上下文里回答。

## 依据

同上下文自查等于让犯错者当裁判 —— 模型会倾向于为自己的答案找理由。依据：FactScore 从 55.9 提升到 71.4。

## 边界：什么情况下它不成立

分解式的代价是 token 成本翻倍且流程更复杂。在成本敏感的场景可以只对高价值候选做，但不能改成同上下文自查。
