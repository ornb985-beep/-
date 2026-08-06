---
id: K-ACQ-026
title: gsxt / 招投标 / SEC EDGAR / 巨潮：已登记的 A 级政府与法定披露源
domain: acquisition
type: fact
maturity: implemented
status: active
evidence_grade: A
n_independent_sources: 2
sample_size:
sources:
  - oic/compliance/provenance.py
  - oic/sources/fetchers.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

国家企业信用信息公示系统、招投标平台、SEC EDGAR、巨潮资讯 均登记为政府公开或法定披露，A 级。

## 依据

gsxt 正是剪刀差缺的那一半（企业注册/注销）。EDGAR 与巨潮是中美招股书的官方入口。

## 边界：什么情况下它不成立

**本环境出网策略阻断 EDGAR(000) 与巨潮/交易所(403)。**代码路径已就绪，取数需在有网络的环境执行。

## 代码位置

`oic/sources/fetchers.py`
