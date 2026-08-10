---
id: K-GOV-001
title: G0 可复现门：双跑逐字节一致
domain: governance
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/00-总纲与终局判据.md
  - oic/scoring/engine.py
  - tests/test_reproducibility.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

同一输入两次运行，结果必须逐字节相同；同输入的排序 100% 稳定。**这道门已通过。**

## 依据

`verify_scores()` 双跑并断言 `to_canonical_json()` 完全相等。另有一条 AST 静态检查测试，确保 `oic/scoring/` 不 `import random / time / datetime`。还有一条**反向测试**证明这个断言真的会失败 —— 否则它可能是个永真的摆设。

## 边界：什么情况下它不成立

它只保证「算得稳」，**完全不保证「算得准」**。一个恒返回 42 的函数也能过 G0。准不准由 G2 判定。

## 代码位置

`oic/scoring/engine.py::verify_scores`
