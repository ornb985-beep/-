---
id: K-ANA-026
title: 盲区地图：完备不可达，但「知道缺什么」可达
domain: analysis
type: method
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - docs/v4/08-操盘手全流程.md
  - docs/v4/11-全景总纲.md
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

系统不追求「无信息盲区」，而是输出每个品类**哪些字段有、哪些没有、来源等级如何分布**。

## 依据

完备性不可达 —— 这是信息获取的物理事实，不是工程不努力。但「知道缺什么」可达，且直接影响决策：缺供给侧就不能谈剪刀差，缺集中度就不能谈格局。

## 边界：什么情况下它不成立

盲区地图本身依赖于「我们知道该有哪些字段」。指标分类学之外的字段仍然是不可见的盲区。
