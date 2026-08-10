---
id: K-STA-015
title: 代理结局必须过 Prentice 准则
domain: statistics
type: criterion
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/calibration/surrogate.py
  - docs/v4/02-公式与算法规范.md
  - docs/v4/07-路线图与回退规则.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

代理指标要能替代真实结局，必须满足 Prentice 准则；不满足则停用其写入校准。

## 依据

不满足 Prentice 的代理会把校准往错误方向拉 —— 系统会越来越擅长优化那个代理，而离真实目标越来越远。

## 边界：什么情况下它不成立

Prentice 准则的检验本身需要同时观测代理与真实结局的样本。在真实结局稀缺时，这个检验也做不了。

## 代码位置

`oic/calibration/surrogate.py`
