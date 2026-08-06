---
id: K-GOV-003
title: G2 有效性门：BS < UNC 且样本 ≥30
domain: governance
type: criterion
maturity: prior
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - docs/v4/00-总纲与终局判据.md
  - oic/calibration/brier.py
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

**只有通过 G2 才允许对外宣称「有效」。** 判据：`BS < UNC`（等价于 `RES > REL`）且 `BSS > 0`，已解析真实结局 ≥30 条。当前 11 条，未通过。

## 依据

Murphy 三分解把 Brier 拆成 REL−RES+UNC。`BS < UNC` 的含义是「比always-predict-base-rate 强」—— 这是「比瞎猜强」最低限度的数学定义。30 条的门槛与 `config.MIN_SAMPLES_FOR_CALIBRATION` 同源。

## 边界：什么情况下它不成立

通过 G2 只说明「在这批样本上比瞎猜强」。样本外表现、以及品类高度相关带来的有效样本量折损，G2 都管不了。

## 代码位置

`oic/calibration/brier.py::brier_skill_score`
