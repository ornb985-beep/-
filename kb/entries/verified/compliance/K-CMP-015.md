---
id: K-CMP-015
title: 计算层版本号变更即隔离历史预测
domain: compliance
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/__init__.py
  - docs/v4/03-数据契约与Schema.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`SCORING_ENGINE_VERSION` 在任何影响数值结果的改动后必须 +1。

## 依据

不区分版本的话，改了公式之后新旧预测会被混在一起做校准，**校准会被静默污染** —— 这类污染没有任何报错。

## 边界：什么情况下它不成立

版本号靠人维护。忘记 +1 不会报错，只会让校准结果变得无意义。

## 代码位置

`oic/__init__.py::SCORING_ENGINE_VERSION`
