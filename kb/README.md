# OIC 知识库

> 把 20 份文档 + 10,099 行代码里的知识，拆成**可查、可追溯、可安全迭代**的原子条目。

```bash
python -m oic.kb --stats            # 全库概况
python -m oic.kb --find 剪刀差       # 搜
python -m oic.kb --show K-STA-016   # 看一条（含完整演化链）
python -m oic.kb --check            # 六条校验
```

---

## 一分钟理解它和「一堆 markdown」的区别

写得再好的 markdown，三个月后一定会变成这样：

| 会发生的事 | 这里怎么拦 |
|---|---|
| 有人加了条没写出处的结论 | 校验器直接报 ERROR，`sources` 为空即拒绝 |
| 出处写了，但指向的文件早没了 | 仓库内路径必须真实存在，否则报错 |
| 有人手填「置信度 0.9」 | `confidence` 是**禁止字段**，解析阶段就抛 |
| 改了一条，引用它的三处 playbook 还指旧说法 | playbook 引用断链即报错 |
| 把被推翻的旧结论删了 | `IDS.txt` 只增不减，删了就报错 |

这五条都不是态度问题，是**没有闸就一定会发生**。

---

## 目录

```
kb/
  INDEX.md        自动生成的全库索引（勿手改）
  TAXONOMY.md     三轴分类学 + 为什么这么分
  SCHEMA.md       条目字段契约
  CHANGELOG.md    演化留痕（自动追加）
  IDS.txt         已发号清单，只增不减
  entries/
    verified/     我们自己验证或实现过的（9 个域）
    external/     通用 AI 方法论 —— **本项目未验证**
  playbooks/      P1–P7 可复用技能流程
```

**`external/` 单独成区不是排版偏好。** 校验器强制那一区的条目
不得单独支撑任何已验证结论 —— 否则「某篇博客这么说」和
「我们跑了 30 个样本」会在同一张表里长得一模一样。

---

## 怎么查

| 我想知道 | 去哪 |
|---|---|
| 现在整体什么状态 | [INDEX.md](./INDEX.md) |
| 免费数据怎么合规地抓 | [P1](./playbooks/P1-免费数据抓取.md) |
| 一个行业怎么查透 | [P2](./playbooks/P2-多角度深度调查.md) |
| 数据怎么防错 | [P3](./playbooks/P3-证据核验与纠错.md) |
| 统计结论怎么不骗自己 | [P4](./playbooks/P4-统计防自欺.md) |
| AI 怎么调度 | [P5](./playbooks/P5-AI调度体系.md) |
| 法律边界在哪 | [P6](./playbooks/P6-合规边界.md) |
| 从零到交付整条链 | [P7](./playbooks/P7-三段式全流程.md) |
| 我们踩过哪些坑 | `--find 教训`，或看 type=lesson 的条目 |
| 哪些结论已经被推翻 | INDEX.md 末尾的「已证伪清单」 |

---

## 怎么加一条

1. 挑域与类型（见 [TAXONOMY.md](./TAXONOMY.md)）
2. 在对应目录建 `K-<域码>-<序号>.md`，字段照 [SCHEMA.md](./SCHEMA.md)
3. **正文三节必填**：`## 断言` / `## 依据` / `## 边界：什么情况下它不成立`
4. `python -m oic.kb --check` 过了再 `--index` 重建索引

第 3 条里的「边界」是必填的，因为**没有边界的断言不是知识，是口号**。

---

## 怎么让它进化

只有两种合法演化，**都不删除任何东西**：

```python
from oic.kb.evolve import supersede, falsify

supersede(store, "K-ANA-012", new_entry, reason="…", on="2026-09-01")
falsify(store, "K-STA-024", falsified_by="K-STA-016", reason="…", on="2026-08-05")
```

`supersede` 把旧条目标 superseded 并双向挂链；
`falsify` 把旧条目标 falsified 并指向推翻它的证据。**原文原样保留。**

### 库里已经有一个验收样本

[K-STA-024](./entries/verified/statistics/K-STA-024.md) 是真的被推翻过的结论：

> n=7 时 ρ=−0.289，我当时写了「方向值得记下来」。
> 样本翻倍到 11 后 ρ=+0.058、p=0.931，方向消失。

这条**没有被删掉**。它留在库里，标着 FALSIFIED，指向推翻它的
[K-STA-016](./entries/verified/statistics/K-STA-016.md)，
并在正文末尾写清楚了教训：**n=7 时哪怕方向讲得通也不能记。**

删掉它，就等于让同一个错误可以再犯一次。

---

## 置信档位

| 档位 | 含义 |
|---|---|
| ✅ CONFIRMED | 关于世界：A 级 + ≥2 独立源 + 样本 ≥30；关于本系统：A 级且已验证 |
| 🟢 SUPPORTED | 证据充分但未达上一档 |
| 🟡 PROVISIONAL | 单源，或样本不足 |
| ⬜ UNVERIFIED | 先验值或外部来源 —— **本项目没有验证过** |
| ❌ FALSIFIED | 已被推翻，保留在库里 |

**刻意不给 0.87 这种数字。** 这套系统在 `predict_probability`、
`conformal`、`kelly` 里都拒绝输出伪精确点值，知识层没有理由破例。

档位由 `(evidence_grade, n_independent_sources, sample_size, maturity)` 推出，
其中有一处刻意的不对称：

- **关于世界的断言**（`type=fact`）要样本量 —— 它可能被下一批数据推翻
- **关于本系统行为的断言**要代码与通过的测试 —— 样本量对它没有意义

「`kelly` 在 n<30 时拒绝输出」这条不需要 30 个样本来证明，
它需要的是一个会失败的测试。

---

## 在你的 App 里用

```python
from oic.sdk import OIC
oic = OIC.for_app(app_name="我的商机助手", contact="you@example.com")

kb = oic.knowledge()
kb.select(domain="acquisition", type="criterion")   # 按三轴过滤
kb.chain("K-STA-024")                               # 完整演化链
kb.falsified                                        # 被推翻的结论（是资产）
```

---

> ⚠️ 本库的合规类条目是工程化的研究性梳理，不构成法律意见。
> 落地前须请执业律师就具体功能做合规审查。
