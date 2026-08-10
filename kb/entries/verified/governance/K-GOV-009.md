---
id: K-GOV-009
title: 失效模式3：归因不可能 —— 赚钱是系统还是执行力
domain: governance
type: antipattern
maturity: verified
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

没有反事实。CATE 需要随机化才能识别因果，但你不可能「为做对照故意不给用户看好商机」。

## 依据

缓解：**只校准可验证的中间指标**（留资率、询单数、退货率），**不校准最终成败**。F5.9 已降级为「匹配度启发式」，禁止宣称因果。

## 边界：什么情况下它不成立

如果有一天存在自然实验（比如系统故障导致部分用户看不到推荐），那段数据可以做准实验识别。但不能为此人为制造。
