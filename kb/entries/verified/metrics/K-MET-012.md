---
id: K-MET-012
title: E1/E2：样本池的排除与保留规则
domain: metrics
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 1
sample_size:
sources:
  - data/research/PROTOCOL.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

**E1** 非品类项（如「餐饮企业上市」是资本事件不是品类）→ 排除。**E2** 采集后若 as-of 数据缺失 → **保留在池中并标记 `insufficient_data`**，不得移出分母。

## 依据

E1 保证样本池的同质性；E2 防止「查不到就不算」造成的幸存者偏差。这两条在采集**之前**冻结，防止事后调整样本池。

## 边界：什么情况下它不成立

E1 的判定有主观性。冻结在采集前是唯一的缓解 —— 事后再改就是 p-hacking。
