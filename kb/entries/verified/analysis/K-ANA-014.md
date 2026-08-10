---
id: K-ANA-014
title: Kano / Berger Better-Worse 系数
domain: analysis
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 3
sample_size:
sources:
  - oic/scoring/differentiation.py
  - docs/v4/02-公式与算法规范.md
  - EXT:Berger et al., Kano's Methods
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

用 Better/Worse 系数把功能归类为魅力型/期望型/必备型/无差异型。

## 依据

必备型做到 100 分也不加分，魅力型做到 60 分就能赢。不做这个区分会把资源投在没有回报的维度上。

## 边界：什么情况下它不成立

分类依赖问卷设计与样本代表性。小样本下类别边界很不稳定。

## 代码位置

`oic/scoring/differentiation.py`
