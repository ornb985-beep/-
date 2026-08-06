---
id: K-EVD-006
title: 真值发现：源可靠度与真值互相迭代
domain: evidence
type: method
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 2
sample_size:
sources:
  - oic/evidence/truth.py
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

多源冲突时，用迭代算法同时估计各源可靠度与最可能的真值，而不是简单取众数或平均。

## 依据

简单平均把可靠源与不可靠源等同对待；取众数则让转引最多的说法获胜 —— 而转引多恰恰可能是同一个源被复制。

## 边界：什么情况下它不成立

迭代算法需要足够多的重叠观测才能识别出可靠度差异。本项目当前的观测密度还不足以让它稳定收敛。

## 代码位置

`oic/evidence/truth.py`
