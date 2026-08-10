---
id: K-CMP-009
title: AI 内容必须同时有显式与隐式标识
domain: compliance
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/compliance/ai_labeling.py
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

GB 45438-2025：正文加显式提示 + 元数据加隐式标识，`assert_labeled()` 任一缺失都不许导出。

## 依据

显式标识给用户看，隐式标识给平台与监管做机器核验。只做其一等于没做。

## 边界：什么情况下它不成立

标识只解决「告知这是 AI 生成」，不解决内容本身的合规性 —— 那是证券边界与其他红线的职责。

## 代码位置

`oic/compliance/ai_labeling.py::assert_labeled`
