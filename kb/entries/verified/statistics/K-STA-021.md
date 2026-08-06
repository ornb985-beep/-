---
id: K-STA-021
title: 回测证明了管线通、防泄漏有效，没证明有效性
domain: statistics
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - data/research/FINDINGS.md
  - data/research/PROTOCOL.md
  - oic/research/backtest.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

已证明：采集→归一→双源锚定→as-of闸→评分→结局回填→统计全流程可复现；`--dry-run` 断言无未来信息。**未证明**：方法论有效（n 太小，ρ 与噪声不可分）；未通过 G2。

## 依据

把「管线通了」和「方法有效」分开陈述，是这次回测最重要的产出。前者是工程结论且已达成，后者是科学结论且还差 19 条结局。

## 边界：什么情况下它不成立

管线可复现不代表管线正确 —— 它可能稳定地算错。正确性由 audit 与单元测试分别保证。
