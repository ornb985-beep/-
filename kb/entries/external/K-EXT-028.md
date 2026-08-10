---
id: K-EXT-028
title: 增量式采纳：先只读，再建议，最后自动执行
domain: external
type: criterion
maturity: external
status: active
evidence_grade: B
n_independent_sources: 1
sample_size:
sources:
  - EXT:业界通行实践
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

AI 能力的上线顺序应当是只读分析 → 给人建议 → 自动执行。

## 依据

每一级的可逆性递减。跳级上线会在还没建立信任时就承担不可逆后果。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

这与本系统的 G0→G4 门禁是同一个思路：**先证明能力，再扩大授权**。
