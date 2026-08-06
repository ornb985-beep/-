---
id: K-ANA-028
title: 概率粒度不宜过细
domain: analysis
type: criterion
maturity: implemented
status: active
evidence_grade: B
n_independent_sources: 1
sample_size:
sources:
  - docs/v4/02-公式与算法规范.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

概率输出限制在有限档位，不给两位小数。

## 依据

判断层的分辨率达不到 1% 的粒度。给出 43% 而不是 40%，多出来的那 3% 是噪声不是信息。

## 边界：什么情况下它不成立

粒度太粗会损失真实的区分度。档位数应当与实测分辨度（Murphy 分解里的 RES）匹配。
