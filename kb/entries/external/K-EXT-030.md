---
id: K-EXT-030
title: 模型输出的自信程度与正确性关联很弱
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

模型说「我确定」不代表更可能对。

## 依据

语言模型的措辞自信度主要由训练语料的表达习惯决定，不是校准过的概率。

**本条未经本项目验证。** 它记录的是业界通行做法，不构成本系统的实测结论。校验器强制它不得单独支撑任何已验证条目。

## 边界：什么情况下它不成立

这是本系统坚持**用外部校准而非模型自陈置信度**的原因。要概率就要 Brier 与 Murphy 分解，不能问模型「你有多确定」。
