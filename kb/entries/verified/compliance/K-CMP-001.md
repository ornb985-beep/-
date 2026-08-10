---
id: K-CMP-001
title: 证券边界的唯一判据：是否触及具体证券
domain: compliance
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/compliance/securities_guard.py
  - docs/v4/06-合规内核.md
  - tests/test_compliance.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

判断一段输出要不要拦，只看它有没有触及**具体证券**，不看它像不像「投资建议」。

## 依据

《证券法》第160条第2款规定从事证券投资咨询业务须经证监会核准。「荐股软件」的认定标准是四项功能，全部围绕**具体证券**展开。

## 边界：什么情况下它不成立

**「投资」二字本身不触发，证券关联才触发。**「初期投入 50 万元」「止损线 15 万」这类纯商业表述不在管辖范围内。

## 代码位置

`oic/compliance/securities_guard.py`
