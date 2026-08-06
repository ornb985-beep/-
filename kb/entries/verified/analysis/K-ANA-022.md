---
id: K-ANA-022
title: 信源独立性：10 个源可能只是 1 个证据
domain: analysis
type: method
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/research/investigate.py
  - docs/v4/12-无限检索与智能体集群.md
  - tests/test_sources.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`assess_independence()` 通过 `KNOWN_ORIGINATORS` 把名义来源折算成**有效独立源**：十篇引用同一家的报道，独立性是 1 不是 10。

## 依据

这是「多方求证」和「多方转引」的分水岭。没有这个折算，智能体集群只会**放大同一个错误**，并且让它看起来被多方确认了。

## 边界：什么情况下它不成立

识别依赖 `KNOWN_ORIGINATORS` 名单的完备性。名单外的一级供应商会被当成独立源，导致独立性被高估。

## 代码位置

`oic/research/investigate.py::assess_independence`
