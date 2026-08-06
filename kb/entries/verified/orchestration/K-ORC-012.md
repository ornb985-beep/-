---
id: K-ORC-012
title: SDK 把纪律一起打包，而不只是转发 import
domain: orchestration
type: method
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

SDK 的每个能力方法都配一条拒绝路径：前置不满足时抛 `Refusal` 子类，而不是返回退化结果。

## 依据

如果 SDK 只是 import 转发，那么调用方里任何一次「这次先跳过 audit」「这次先不加 AI 标识」都会成立 —— 赶进度时一定有人这么写。

## 边界：什么情况下它不成立

`Refusal` 在调用方应当被渲染成「暂不能给结论，因为⋯⋯」，而不是 catch 掉填默认值。SDK 管不住这一步，只能把理由写进异常消息里。

## 代码位置

`oic/sdk.py::Refusal`
