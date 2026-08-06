---
id: K-GOV-015
title: 失效模式9：LLM 判断层的天花板 = 普通人
domain: governance
type: antipattern
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/07-路线图与回退规则.md
  - docs/v4/00-总纲与终局判据.md
  - tests/test_calibration.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

ForecastBench：最强 LLM Brier **0.122** ≈ 普通公众 **0.121**，远不如超级预测者 **0.096**。**换模型突破不了这个天花板。**

## 依据

含义：超过普通人只能靠**架构**（证据地基、确定性计算、校准），不能靠换模型。更进一步：没有人的终审，系统达不到超预水平 —— 「全智能」有硬上限。这三个数字钉进了单元测试，防止自我感觉良好。

## 边界：什么情况下它不成立

这是 2024 年的基准。模型能力若真有代际跃迁，需要重测而非假设。但在重测之前，不得假设已经突破。

## 代码位置

`tests/test_calibration.py`（ForecastBench 基准值断言）
