---
id: K-EVD-010
title: 检索摘要不是原文，中间多一层误差
domain: evidence
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - data/research/FINDINGS.md
  - data/research/PROTOCOL.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

检索工具返回的是摘要而非原始网页，摘要层可能改写数字表述（如把「万」译成 million）。

## 依据

本项目那次 100× 错误就发生在摘要层。缓解措施：原文片段与 URL 全部留存，且每个数字过字符级校验。

## 边界：什么情况下它不成立

在拿不到原始网页的环境里（本环境 WebFetch 被出网策略阻断），摘要是唯一可得的。那时**必须**依赖字符级校验作为最后防线。
