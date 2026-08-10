---
id: K-ANA-020
title: 变化率分类与评分必须分开
domain: analysis
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 1
sample_size:
sources:
  - oic/research/velocity.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`classify()` 是纯算术（趋势方向、幅度、形状），`velocity_score()` 才引入 PRIOR 权重做判断。

## 依据

分开之后，算术部分可以被严格测试，而判断部分的 PRIOR 值可以在不动算术的前提下重新校准。

## 边界：什么情况下它不成立

分界线的位置本身是设计选择。把「什么算 UP」也当成判断的话，分类也会带 PRIOR。

## 代码位置

`oic/research/velocity.py::classify`
