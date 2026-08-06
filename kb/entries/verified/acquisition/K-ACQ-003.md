---
id: K-ACQ-003
title: 反爬是停止信号，不是待修的 bug
domain: acquisition
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/09-方案融合与缺口.md
  - oic/sources/http_fetch.py
  - oic/compliance/provenance.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

遇到反爬的正确回应是**从源清单里移除该站或走授权渠道**，不是修抓取器。

## 依据

用户提供的抓取记录里，微博热搜与知乎热榜标注「反爬，待修」。在第13条第3款下，「修」这个动作本身就是构成要件。

## 边界：什么情况下它不成立

限速被拒（429）与技术对抗（验证码、指纹）性质不同：前者降频后可继续，后者应当停止。`NO_RETRY_STATUSES` 对两者一视同仁地停，是刻意的保守。

## 代码位置

`oic/sources/http_fetch.py::NO_RETRY_STATUSES`
