---
id: K-ORC-013
title: capabilities() 让「还不能干什么」可被程序读出
domain: orchestration
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/sdk.py
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`OIC.capabilities()` 返回结构化的能力清单，其中 `effectiveness` 恒为 False，`probability` 在 n<30 时为 False。

## 依据

如果「现在还不能干什么」只写在文档里，它会被产品页面盖掉。写成方法，产品就必须显式忽略它才能撒谎。

## 边界：什么情况下它不成立

它报告的是**当前配置下**的能力。换一份 registry、换一个样本量，结果就变 —— 这正是它该有的行为。

## 代码位置

`oic/sdk.py::OIC.capabilities`
