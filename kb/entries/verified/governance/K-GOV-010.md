---
id: K-GOV-010
title: 失效模式4：代理结局的 Goodhart 效应
domain: governance
type: antipattern
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/07-路线图与回退规则.md
  - oic/calibration/surrogate.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

优化 14 天留资率 ≠ 优化赚钱。代理指标一旦成为目标，就不再是好指标。

## 依据

双通道 + `assert_channel` 抛 PermissionError：代理结局与真实结局物理分开两条通道，代理不得写入真实校准。

## 边界：什么情况下它不成立

代理指标仍然有用 —— 它是唯一能快速反馈的信号。问题只在于把它当成终局。

## 代码位置

`oic/calibration/surrogate.py::assert_channel`
