---
id: K-GOV-013
title: 失效模式7：污染检测误报多于真报
domain: governance
type: antipattern
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/07-路线图与回退规则.md
  - oic/config.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

Benford 定律不适用于有价格分档的电商数据；突变点检测在大促必炸。

## 依据

三个检测器默认 `enabled=false`，必须先通过对抗集才可开启。默认关闭是因为**误报会让人关掉整道闸** —— 这正是历史上闸门失效的主因。

## 边界：什么情况下它不成立

如果某天有了合适的对抗集并验证了误报率，可以逐个开启。但不得因为「看起来应该有用」就打开。

## 代码位置

`oic/config.py::PollutionDetectors`（全部默认 False）
