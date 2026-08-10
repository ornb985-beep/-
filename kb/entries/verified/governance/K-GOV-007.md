---
id: K-GOV-007
title: 失效模式1：地基未验证 —— C/O/D/E 四维从未被证明有预测力
domain: governance
type: antipattern
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/07-路线图与回退规则.md
  - oic/config.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

共形预测、CATE、真值发现都是在**给定特征集**上做得更精确。特征集若是错的，它们只会把错的东西算得更自信。

## 依据

四维权重全部标 `PRIOR`，`uncalibrated_notice()` 强制界面显示「未校准」。这是结构性风险，前三条失效模式加再多算法都修不好。

## 边界：什么情况下它不成立

如果某天四维被证明有预测力，这条自动降级为历史记录。在那之前它是本系统最大的悬空点。

## 代码位置

`oic/config.py::Weights`（全部 PRIOR）
