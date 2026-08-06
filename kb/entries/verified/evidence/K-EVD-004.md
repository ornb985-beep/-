---
id: K-EVD-004
title: 双源锚定：有效独立源 <2 一律标待核实
domain: evidence
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/research/dossier.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

同一指标至少需要 2 个**有效独立**来源才算锚定，否则标记「待核实」。

## 依据

单源结论无法区分「事实」与「某一家的口径」。而口径差异在本项目实测中极大：预制菜 2022 规模 2271亿 vs 4196亿，差 85%。

## 边界：什么情况下它不成立

关键在「有效独立」而不是「个数」。十篇转引同一家的报道仍然是 1 个源 —— 见信源独立性折算。

## 代码位置

`oic/research/dossier.py`
