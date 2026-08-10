---
id: K-STA-020
title: 双标签：需求侧作副标签，商机侧作主标签
domain: statistics
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - data/research/PROTOCOL.md
  - data/research/FINDINGS.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

结局定义冻结为两个标签：`outcome_demand`（需求侧，机械可查）与 `outcome_opportunity`（商机侧）。**主标签应当用商机侧。**

## 依据

上一条实测显示需求侧标签会误导。两个标签都保留是为了能观察到它们打架 —— 只留一个就看不见这个现象了。

## 边界：什么情况下它不成立

商机侧标签的判定主观性更强，机械可查性更差。这是用可判定性换正确性的取舍，需要在结局定义里写死判据。
