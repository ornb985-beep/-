---
id: K-EVD-003
title: 我把「3.81万」记成 3,810,000 —— 100 倍单位错
domain: evidence
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - data/research/FINDINGS.md
  - oic/research/audit.py
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

露营企业新增注册数，原文「3.81**万**家」，我从检索摘要手工转录成 `3,810,000`。摘要层把「万」译成了 million。

## 依据

**这不是来源矛盾，是我绕过了自己建的字符级校验。**原始序列 1.29/2.54/3.81/7.03 万家、存量 22.34 万家完全自洽。现已由 `audit.check_grounding` 抓出并修正，且写成回归测试。

## 边界：什么情况下它不成立

教训的适用范围比这一次宽：**任何手工转录都要过校验**，包括「我很确定」的时候 —— 尤其是那时候。

## 代码位置

`oic/research/audit.py::check_grounding`
