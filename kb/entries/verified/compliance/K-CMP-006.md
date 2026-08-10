---
id: K-CMP-006
title: 证券边界 S5：高危措辞自动改写
domain: compliance
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/compliance/securities_guard.py
  - tests/test_compliance.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

「投资级决策建议」→「商业/市场机会分析」；「投资建议」→「商业机会评估」；「投顾服务」→「商业研究服务」。**改写后放行，不阻断。**

## 依据

这类措辞本身不违法，但会给人「我们在做投顾」的印象。自动改写既降低误解风险，又不影响实质内容。

## 边界：什么情况下它不成立

S5 与 S1–S4 的处理方式**完全相反**。分界线是：措辞问题可以改，实质触及具体证券不能改。

## 代码位置

`oic/compliance/securities_guard.py::SAFE_REWRITES`
