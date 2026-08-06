---
id: K-ANA-024
title: 零产出角度 = 数据不存在，不是查得不够
domain: analysis
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/research/investigate.py
  - data/research/SATURATION.md
  - data/research/FINDINGS.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

某个角度多次查询后产出恒为 0，判定该字段大概率不存在于公开渠道。

## 依据

**这是整套方法里最省钱的一条判定。**它把「再查查看」和「这数据根本不存在」区分开 —— 后者继续查是纯浪费，该做的是换渠道（付费源/招股书）或接受盲区。实测：即时零售的 `capital` 角度真零产出。

## 边界：什么情况下它不成立

零产出也可能是查询串写得不对。判定前应当至少换过一次表述方式。

## 代码位置

`oic/research/investigate.py::SaturationReport.angles_empty`
