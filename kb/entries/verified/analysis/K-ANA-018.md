---
id: K-ANA-018
title: 无供给侧证据时排序分封顶 0.6
domain: analysis
type: parameter
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/scoring/attention.py
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`NO_SUPPLY_EVIDENCE_CAP = 0.6`。只有热度、没有供给侧证据的候选，排序分封顶。

## 依据

**这个约束的依据是公式定义，不是数据拟合**：剪刀差需要两侧数据，缺一侧时这个商机的核心判据根本没算。封顶表达的是「这条还没被真正评估过」。

## 边界：什么情况下它不成立

刻意**不加**热度惩罚项 —— 那会是在拟合 n=7 的噪声。0.6 这个具体数值是 PRIOR。

## 代码位置

`oic/scoring/attention.py::apply_cap`
