---
id: K-EXT-020
title: 幻觉率随任务熟悉度下降而上升
domain: external
type: fact
maturity: external
status: active
evidence_grade: B
n_independent_sources: 1
sample_size:
sources:
  - EXT:业界通行实践
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

模型在训练数据覆盖稀疏的领域更容易编造。

## 依据

冷门领域、最新事件、专有内部知识是幻觉高发区。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

这解释了为什么本系统对**中文细分品类的供给侧数据**坚持字符级 grounding —— 那正是覆盖最稀疏的地方。
