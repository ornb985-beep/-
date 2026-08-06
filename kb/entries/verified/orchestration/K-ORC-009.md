---
id: K-ORC-009
title: 漏斗自洽性必须在启动时炸，而不是线上第 13 次
domain: orchestration
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/pipeline/budget.py
  - docs/v4/09-方案融合与缺口.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`assert_funnel_feasible()` 在启动时检查：漏斗不能变宽、相邻级输入输出对得上、各级总成本 ≤ 硬顶。

## 依据

它抓到过一个真实矛盾：设计文档里同时写着「LLM ≤12 次/天」与「LLM 精评每天约 1000 次调用」。**差 83 倍，两者不可能同真。**这类矛盾在启动时是一行报错，在线上是第 13 次调用时的神秘失败。

## 边界：什么情况下它不成立

无限硬顶时成本检查自动跳过，但结构检查（不能变宽、要对得上）仍然执行。

## 代码位置

`oic/pipeline/budget.py::assert_funnel_feasible`
