---
id: K-EVD-001
title: 每个数字必须能用字符偏移回到原文
domain: evidence
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/evidence/grounding.py
  - docs/v4/02-公式与算法规范.md
  - tests/test_evidence.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`verify_claim()` 校验：span 在范围内、span 非空、span 内确实存在该数值。对不上就**丢弃，不近似**。

## 依据

这是幻觉在数值层面的唯一有效防线。「有出处」如果不能精确到字符，就只是一种说法。

## 边界：什么情况下它不成立

它只能验证「这个数字出现在这段原文里」，不能验证「这个数字是对的」—— 原文本身可能错。那是双源锚定与 audit 的职责。

## 代码位置

`oic/evidence/grounding.py::verify_claim`
