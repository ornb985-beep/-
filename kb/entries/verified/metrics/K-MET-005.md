---
id: K-MET-005
title: as-of 时间闸：未来信息进来直接抛错
domain: metrics
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/research/asof.py
  - tests/test_research.py
  - data/research/PROTOCOL.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

`assert_no_lookahead()` 在观测的 `published_at` 晚于 as-of 日时抛 `LookaheadError`。

## 依据

前视偏差是回测最常见也最致命的错误，而且它不会报错，只会让结果好看。做成异常是唯一可靠的防线。有一条测试专门把 2025 年的观测喂进 2022 年评分并断言抛错。

## 边界：什么情况下它不成立

它只能拦住有明确发布日期的观测。无日期的观测由「一律排除」规则处理，而不是猜一个日期。

## 代码位置

`oic/research/asof.py::assert_no_lookahead`
