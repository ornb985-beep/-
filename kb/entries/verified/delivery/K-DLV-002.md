---
id: K-DLV-002
title: 90 天四阶段，每阶段带量化止损门槛
domain: delivery
type: method
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/deliver/plan_90day.py
  - docs/v4/08-操盘手全流程.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

四个阶段各有明确的进入条件与**量化止损线**，复用 `config.TrackProfile.stage_gates`。

## 依据

没有止损线的计划会一直执行到钱花完。把止损写进计划本身，而不是靠执行者临场判断。

## 边界：什么情况下它不成立

止损阈值是 PRIOR，需要按具体品类与预算调整。系统给的是结构，不是可以照抄的数字。

## 代码位置

`oic/deliver/plan_90day.py::build_plan`
