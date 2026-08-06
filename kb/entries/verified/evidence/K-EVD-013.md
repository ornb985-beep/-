---
id: K-EVD-013
title: 我知道后续事实，这个偏差只能压制不能消除
domain: evidence
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - data/research/PROTOCOL.md
  - data/research/FINDINGS.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

回顾性回测中，执行者已经知道 2025 年的结果。四条防护（样本池取自当年榜单、结局定义先冻结、as-of 代码强制、原样留证）**只能压制不能消除**事后诸葛。

## 依据

把这条明写出来，是为了防止「我们做了防护所以没问题」这种自我安慰。唯一的根治是前瞻性预测 —— 先记录预测，再等结局发生。

## 边界：什么情况下它不成立

commit 时间戳是防护的一部分：结局定义的提交必须早于结局采集。这提供了可核查的证据，但仍不等于双盲。
