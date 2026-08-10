---
id: K-ORC-011
title: 人机边界：模型不做终审
domain: orchestration
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/04-Agent契约.md
  - docs/v4/07-路线图与回退规则.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

模型负责抽取、评分、生成候选；**终审、放行、对外承诺由人做**。

## 依据

ForecastBench 显示 LLM 判断层的天花板约等于普通人。超过普通人只能靠架构 + 人的终审，不能靠换模型。

## 边界：什么情况下它不成立

这条限制了自动化程度的上限。「全自动」在这个天花板下是做不到的，硬做只会把普通人水平的判断规模化。
