---
id: K-ACQ-024
title: 百度/头条/抖音热榜：可登记但需逐个法务放行
domain: acquisition
type: fact
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 2
sample_size:
sources:
  - oic/compliance/provenance.py
  - docs/v4/09-方案融合与缺口.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

这三个榜单当前抓取正常，登记为 C 级来源，但仍需填 ToS 链接与法务结论才会出现在白名单里。

## 依据

「当前能抓」不等于「允许抓」。白名单要的是授权依据，不是技术可行性。

## 边界：什么情况下它不成立

热榜是需求侧信号，且**只有热度没有供给侧**。单靠热榜无法算剪刀差 —— 这正是 `attention.py` 封顶 0.6 的原因。

## 代码位置

`oic/compliance/provenance.py`
