---
id: K-GOV-008
title: 失效模式2：Outcome 零条 → 七个模块空转
domain: governance
type: antipattern
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/07-路线图与回退规则.md
  - oic/scoring/kelly.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

Brier / Murphy / BSS / 分层贝叶斯 / 共形 / Kelly / CATE **全部**需要真实结局。没有结局，它们不是「不准」，是「无法运行」。

## 依据

缓解方式不是给默认值，是**拒绝输出**：Kelly 返回 `refused=True`，共形返回 NaN 区间，Murphy 分解不计算。

## 边界：什么情况下它不成立

拒绝输出会让产品看起来「什么都不会」。这是真实状态的如实呈现，不是缺陷 —— 掩盖它才是缺陷。

## 代码位置

`oic/scoring/kelly.py::position_size`
