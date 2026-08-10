# 条目字段契约

契约的唯一实现在 `oic/kb/schema.py`。这份文档是它的人读版本 ——
**两者冲突时以代码为准**，因为代码是会被执行的那一份。

---

## 完整示例

```markdown
---
id: K-STA-016
title: 需求增速与结局的相关性与噪声不可分
domain: statistics
type: fact
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 3
sample_size: 11
sources:
  - data/research/FINDINGS.md
  - oic/stats/resample.py
  - oic/research/backtest.py
tags:
supersedes:
superseded_by:
falsified_by:
iteration: 1
reviewed_on: 2026-08-05
---

## 断言

一句话，可证伪。

## 依据

数字 + 出处。

## 边界：什么情况下它不成立

必填。

## 代码位置

可选。
```

---

## 字段

| 字段 | 必填 | 说明 |
|---|:--:|---|
| `id` | ✅ | `K-<三字母域码>-<三位数字>`。**发出即不可改**，域码必须与 `domain` 一致 |
| `title` | ✅ | 一行，能独立看懂 |
| `domain` | ✅ | 10 个域之一 |
| `type` | ✅ | fact / method / criterion / parameter / antipattern / lesson |
| `maturity` | ✅ | verified / implemented / prior / falsified / external |
| `status` | ✅ | active / superseded / falsified |
| `evidence_grade` | ✅ | A / B / C / D |
| `n_independent_sources` | ✅ | **有效独立**源数，不得超过 `sources` 条数 |
| `sample_size` | | 关于世界的断言必填；关于本系统行为的断言留空 |
| `sources` | ✅ | 列表。仓库内路径**必须真实存在**；外部文献写 `EXT:<文献>` |
| `tags` | | 自由标签 |
| `supersedes` | | 本条取代了哪条。填了则 `iteration` 必须 ≥2 |
| `superseded_by` | | 本条被哪条取代。`status=superseded` 时必填 |
| `falsified_by` | | 是什么推翻了本条。`status=falsified` 时**必填** |
| `iteration` | ✅ | 版次，从 1 开始 |
| `reviewed_on` | | 最近复核日期 |

### 禁止字段

`confidence` / `certainty` / `score` / `reliability` / `trust`
—— 出现即在解析阶段抛错。

置信度由 `derive_band()` 从证据结构确定性推出。
**允许手填等于允许通胀**：每个人都觉得自己那条挺可靠。

---

## 正文三节必填

| 小节 | 写什么 |
|---|---|
| `## 断言` | 一句话，**可证伪**。不写「XX 很重要」这类无法被推翻的话 |
| `## 依据` | 数字 + 出处。为什么应该相信这条 |
| `## 边界：什么情况下它不成立` | **必填** |

第三节必填是刻意的。**没有边界的断言不是知识，是口号。**
一条不说明适用范围的规则，会在不适用的场景被照搬，
然后所有人得出「这套方法没用」的结论 —— 而问题出在它被用错了地方。

可选的第四节 `## 代码位置` 指向具体实现。

---

## 七条校验（`oic/kb/check.py`）

| # | 规则 | 违反 |
|---|---|---|
| ① | `sources` 非空，且仓库内路径真实存在 | ERROR |
| ② | 无禁止字段 | 解析即抛 |
| ③ | external 不得单独支撑已验证条目 | ERROR |
| ④ | `falsified` 必有 `falsified_by`；已发 id 不许消失 | ERROR |
| ⑤ | supersede 链双向一致、指向存在、不成环 | ERROR |
| ⑥ | playbook 引用 `[K-XXX-NNN]` 必须解析得到 | ERROR |
| ⑦ | 正文里 `` `目录/文件.py::符号` `` 形式的引用必须真实存在 | ERROR |

「出处指向不存在的文件」比「没有出处」更危险 —— **它看起来是有依据的**。

第 ⑦ 条只查带 `/` 的路径。裸文件名（如 `` `overfit.py` ``）算散文提及，
不查 —— 初版不分这两者，立刻产生 3 个误报。**误报会把人逼着关掉这道闸**
（见 `K-GOV-013`）。符号用宽松匹配：出现在 docstring 里也算通过。

---

## 置信档位推导

```
FALSIFIED    status == falsified
UNVERIFIED   maturity ∈ {prior, external}

type == fact（关于世界）：
  CONFIRMED    A 级 + 独立源 ≥2 + 样本 ≥30
  SUPPORTED    A/B 级 + 独立源 ≥2
  PROVISIONAL  其余

其他 type（关于本系统行为）：
  CONFIRMED    verified + A 级
  SUPPORTED    verified/implemented + A/B 级
  PROVISIONAL  其余
```

样本门槛 30 与 `oic/config.py::MIN_SAMPLES_FOR_CALIBRATION` 同源；
双源门槛与证据层的双源锚定同源。**知识库的判据不自己造，复用系统已有的。**
