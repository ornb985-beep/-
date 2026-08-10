---
id: K-ANA-009
title: 资源系数恒为 0.2，永不参与学习
domain: analysis
type: parameter
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/config.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`RESOURCE_COEFF = 0.2` 硬编码，不在 `Weights` 里，不被影子权重机制修改。

## 依据

**资源约束是物理事实，不因用户偏好改变。**让它参与学习，等于允许系统学会「忽略这个人没钱」。

## 边界：什么情况下它不成立

0.2 这个具体数值仍是 PRIOR。不可学习的是「它是常数」这件事，不是「它等于 0.2」。

## 代码位置

`oic/config.py` 的 `RESOURCE_COEFF`
