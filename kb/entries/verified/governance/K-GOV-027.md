---
id: K-GOV-027
title: 现在不能说的六句话
domain: governance
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/11-全景总纲.md
  - data/research/FINDINGS.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

在 G2 通过之前，以下表述不得出现在任何对外材料里：「预测准确率 X%」「已校准」「剪刀差有效」「无信息盲区」「全网抓取」「躺赚」。

## 依据

逐条对应的事实：G2 未过 n=11；已解析结局 11<30；剪刀差 n=5 且 ρ=0.289 未达 0.3 判据；供给侧覆盖 5/30；SCRAPING 源永不放行所以抓的是站点允许的部分；系统给的是可证伪条件区间不是承诺。

## 边界：什么情况下它不成立

能说的是：可复现、可审计、每个数字能回到原文字符、以及**它会告诉你它不知道什么**。

## 代码位置

`oic/sdk.py::OIC.capabilities`（`effectiveness` 恒为 False）
