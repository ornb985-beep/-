---
id: K-STA-022
title: 品类高度相关，有效样本量比 n 更小
domain: statistics
type: lesson
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

样本多为消费品类，同受 2023–24 消费下行影响。n=11 的**有效**样本量显著小于 11。

## 依据

相关样本会让置信区间被低估、p 值被高估其可靠性。报告 n 而不提相关性，是小样本研究里最常见的自欺方式之一。

## 边界：什么情况下它不成立

没有对有效样本量做正式估计（那需要估计品类间相关结构）。当前只做定性提示。
