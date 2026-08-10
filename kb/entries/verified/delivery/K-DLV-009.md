---
id: K-DLV-009
title: 拒绝输出是正常分支，应当渲染给用户看
domain: delivery
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/sdk.py
  - docs/v4/10-嵌入你的App.md
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`Refusal` 及其子类应当在 App 里渲染成「暂不能给结论，因为⋯⋯」，**不是 catch 掉填默认值**。

## 依据

异常消息里已经写了替代方案（如「相对排序不需要校准」），可以直接展示。把拒绝藏起来等于把系统的诚实藏起来。

## 边界：什么情况下它不成立

SDK 无法强制调用方这么做。它只能把理由写进异常消息，并在文档里说明。

## 代码位置

`oic/sdk.py::Refusal`
