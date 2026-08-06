---
id: K-STA-017
title: 我曾把 ρ=−0.289 过度解读成「方向值得记下来」
domain: statistics
type: lesson
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - data/research/FINDINGS.md
  - oic/stats/overfit.py
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

n=7 时我写过「方向和直觉相反，值得记下来」。样本翻倍后方向消失，这段已删除并标注为被证伪。

## 依据

`overfit.py` 当时就给出了判据：n=7 时纯随机的 |ρ| 中位数**正好是 0.289**。数字当时就说清楚了，是我又多说了一句。**教训：n=7 时哪怕方向讲得通也不能记。**

## 边界：什么情况下它不成立

我当时确实标了「不显著」。但标注不显著之后又写一段解释它为什么合理，读者记住的是解释不是标注 —— 这就是过度解读的实际形态。
