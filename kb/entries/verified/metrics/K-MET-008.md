---
id: K-MET-008
title: 部分之和必须约等于整体
domain: metrics
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 1
sample_size:
sources:
  - oic/research/audit.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

B端 + C端 应当约等于整体规模，超出容差即报警。

## 依据

口径冲突常表现为分项加总对不上整体。实测验证过：预制菜 4200 + 1973 = 6173，与整体口径一致。

## 边界：什么情况下它不成立

容差需要考虑分类不完备（可能还有第三类）与统计时点差异。严格相等的检查会产生大量误报。

## 代码位置

`oic/research/audit.py::check_parts_sum`
