---
id: K-ORC-010
title: 输出前的三道强制闸门
domain: orchestration
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/06-合规内核.md
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

任何到达用户眼前的文本必须依次经过：**① 证券边界（S1–S4 硬违规阻断）→ ② AI 双标识 → ③ 标识校验**。`sdk.export()` 是唯一出口。

## 依据

把闸门做成「唯一出口」而不是「记得调用」，是因为赶进度时一定会有人忘记调用。

## 边界：什么情况下它不成立

S5（措辞类）会被自动改写；S1–S4 **不自动改写** —— 改写掩盖问题，而这类内容根本不该被生成出来。

## 代码位置

`oic/sdk.py::OIC.export`
