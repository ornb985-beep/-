---
id: K-CMP-008
title: 证券违规的罚则量级
domain: compliance
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/compliance/securities_guard.py
  - docs/v4/06-合规内核.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

《证券法》第213条：责令改正、没收违法所得、并处 **1–10 倍**罚款；无/不足 50 万违法所得的处 **50万–500万**，责任人 **20万–200万**；可升级为刑法 225 条非法经营罪。

## 依据

把罚则写进代码注释，是为了让后来的维护者知道这道闸为什么值得写代码，而不是写在文档里就行。

## 边界：什么情况下它不成立

罚则的具体适用取决于情节。这条是量级参考，不是法律意见。

## 代码位置

`oic/compliance/securities_guard.py` 模块 docstring
