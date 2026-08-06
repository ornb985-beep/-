---
id: K-ORC-001
title: 铁律1：确定性计算与 LLM 判断物理隔离
domain: orchestration
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

`oic/scoring/` 与 `oic/calibration/` **零网络、零时钟、零随机**。LLM 在整个系统里只有一个角色：给 C/O/D/E 四维打分。其余全部是确定性计算。

## 依据

隔离不是风格偏好，是可复现性的**前提**：只要计算层里有一次模型调用，`verify_scores` 的双跑一致就不可能成立，整个审计链就断了。一条 AST 静态检查测试守着这条边界。

## 边界：什么情况下它不成立

隔离的代价是计算层无法利用模型的灵活性。这个代价是刻意付的 —— 灵活性换不来可审计性。

## 代码位置

`oic/scoring/engine.py::compute_all_scores`
