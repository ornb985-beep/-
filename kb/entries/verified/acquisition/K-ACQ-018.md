---
id: K-ACQ-018
title: 招股书是供给侧数据的最优公开来源
domain: acquisition
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size:
sources:
  - oic/sources/filing_parse.py
  - docs/v4/11-全景总纲.md
  - oic/sources/fetchers.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

招股书**审计过、有法律责任、「行业竞争格局」是强制披露项**，含市占率、CR5、同业公司数、行业规模与增速、客单价、毛利率、获客成本。登记为 A 级 + `PUBLIC_DOWNLOAD`。

## 依据

这些字段恰好是公开检索渠道最缺的（实测供给侧覆盖 5/30）。法定公开披露不是爬取，不触发 SCRAPING 禁令。

## 边界：什么情况下它不成立

**幸存者偏差**：能 IPO 的都是成功者。**自利披露倾向**：行业规模往大了说、竞争往分散了说对发行人有利。两者都需要在权重上体现，不能直接当客观事实用。

## 代码位置

`oic/sources/filing_parse.py`
