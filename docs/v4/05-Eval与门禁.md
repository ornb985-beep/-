# 05 · Eval 与门禁

**不测量就不可能提高正确率。**

专家共识：好坏 agent 系统的差距几乎从不在框架，
而在 **eval 流水线、可观测性、失败恢复逻辑**。

---

## 一、三级指标

| 级 | 指标 | 回答什么问题 | 实现 |
|---|---|---|---|
| 抽取级 | span P/R/F1 | 证据抽对了吗 | `eval/metrics.py::span_prf` |
| 判断级 | Cohen's κ、容差一致率 | 打分与人工一致吗 | `cohen_kappa` / `score_band_agreement` |
| 系统级 | NDCG@10、Brier | 排序和概率有用吗 | `ndcg_at_k` / `calibration/brier.py` |

### 抽取级细节

IoU ≥0.5 匹配（默认），而非精确匹配 —— 标注者对"哪几个字算证据"本身就有分歧。
**一个 gold span 不能被两个预测重复认领**（已测）。

### 判断级的现实预期

**参照物：GoEmotions 的 27 类情绪标注，标注者间 κ 仅约 0.27。**

所以对细粒度判断任务不要期待 κ>0.8；**0.4–0.6 已算可用**。
如果你的 κ 报出 0.9，先怀疑标注泄漏，而不是庆祝。

同时报"容差一致率"（|机器分 − 人工分| ≤10 的比例）——
对 0–100 分的打分任务比精确相等更贴合。

### 系统级：为什么是 NDCG 而不是准确率

用户实际消费的是**排序后的 top-10**，不是每个商机的绝对分。
NDCG 直接测"系统排的序和人工理想排序有多接近"。

---

## 二、Golden Dataset

文件：[`data/golden.seed.jsonl`](../../data/golden.seed.jsonl)（当前 0 条）

```json
{"opportunity_id":"G-001",
 "category":"户外露营",
 "human":{"c":82,"o":70,"d":88,"e":75,"rank":1},
 "machine":{"c":80,"o":74,"d":85,"e":72},
 "spans":{"predicted":[[10,15]],"gold":[[10,16]]}}
```

**目标规模 50–100 条。低于 30 条时判断级指标方差极大，只看方向。**

### 怎么产出（不要浪费 Wave 0）

Wave 0 手工跑 2 个品类完整流程时，把每个商机的人工四维打分、
人工排序位次、关键证据 span 记下来 —— **那批手工结果就是第一批标注数据。**

这是唯一不需要额外投入就能拿到 golden set 的时机。

---

## 三、对抗 eval 集

验证 F2.6 污染检测（当前默认关闭）。用例类型：

| 类型 | 构造方式 |
|---|---|
| 假月销 | 伪造跨数量级的销量序列 |
| 模板化好评 | 同一句式批量改写 |
| 软文 | C 级来源出现成交证据词 |
| 陈旧数据 | 快照哈希与当前原文不符 |

`evaluate_adversarial([(case_id, caught), ...])` 输出拦截率与漏网名单。

**F2.6 的三个检测器必须先通过对抗集才允许 `enabled=true`。**
理由：Benford 要求跨数量级自然分布，电商有价格分档和平台舍入会误伤正常品类；
突变点检测在 618/双11 会疯狂误报。

---

## 四、CI 门禁

```bash
python -m oic.eval.run --golden data/golden.seed.jsonl --gate
```

| 指标 | 基线（PRIOR） |
|---|---|
| span F1 | ≥0.70 |
| 容差一致率 | ≥0.60 |
| NDCG@10 | ≥0.70 |

退化即以非零码退出，阻断合并。

### 空集时优雅跳过

golden 集为 0 条时输出：

```
golden set 未建立（0 条）。
这不是失败：Wave 0 的手工品类验证结果就是第一批标注数据，
跑完后写进 data/golden.seed.jsonl 即可让本报告开始工作。

⚪ golden set 未建立，门禁跳过
```

**故意的设计**：一个常红的 CI 会被团队学会忽略，那比没有 CI 更糟。

---

## 五、自检套件（零依赖，随时可跑）

```bash
python -m unittest discover -s tests -v          # 154 项，全绿
python -m unittest tests.test_reproducibility    # G0 门
python -m oic.scoring.kelly --selftest           # Kelly 三重安全阀
python -m oic.calibration.report --selftest      # Brier/Murphy/分层/代理
python -m oic.compliance.securities_guard --selftest   # 100% 拦截 / 0 误杀
python -m oic.evidence.grounding --selftest      # span 字符级校验
```

### 关键测试的意图

| 测试 | 验的是什么 |
|---|---|
| `test_injecting_nondeterminism_makes_verify_fail` | **断言本身有效** —— 一个永远通过的断言等于没有断言 |
| `test_engine_module_imports_no_nondeterministic_stdlib` | AST 静态检查：计算层不得 import `random/time/datetime/secrets/uuid` |
| `test_redline_cannot_be_offset_by_high_scores` | 满分商机 + 一条红线 = 0 |
| `test_c_grade_never_counts` | 竞品自称"月销破万"骗不到 1.2 系数 |
| `test_zero_false_positives_on_business_analysis` | 证券拦截器 0 误杀 —— **误杀会逼团队关掉这道闸** |
| `test_reprints_do_not_create_fake_multisource` | 十篇转载仍只算一条 |
| `test_source_cannot_inflate_by_posting_more` | 刷条数无法提高真值发现里的影响力 |
| `test_refuses_without_calibration` | 样本 <30 时 Kelly 拒绝输出仓位 |
| `test_llm_ceiling_reference` | 把 ForecastBench 基准钉进代码 —— 报出 0.05 就是数据泄漏 |
| `test_empty_golden_set_is_graceful` | 空 golden 集不让 CI 常红 |

---

## 六、可观测性（待建）

| 项 | 阈值 / 动作 |
|---|---|
| trace | 每次 agent 调用全链路 |
| 成本 | 按商机、按 agent 归因 |
| **重试率** | **≥2 即报警改 schema，而非加重试** |
| 模型漂移 | 模型快照锁定 + 定期回归 golden set |
| 丢弃率 | span grounding 丢弃率 >30% 即报警改提示词 |

最后两条已在代码里给出提示文案：

> ⚠️ 丢弃率 >30% —— 这不是数据问题，是抽取提示词或 schema 有问题。
> 应改提示词，而不是放宽校验。

---

## 七、eval 之外：G1–G4 的验收方式

| 门 | 怎么验 |
|---|---|
| G1 有区分度 | 用 5 个真实品类跑 `compute_all_scores`，检查剪刀差 M / 切换势能 / 成熟度 L 是否塌缩成同一档 |
| G2 比瞎猜强 | `python -m oic.calibration.report --forecasts <archive>`，看 `RES > REL` 是否通过 |
| G3 比人省 | 同批商机上系统 top-10 vs 人工 top-10 的实际成功率；或同等命中率下的人工工时 |
| G4 有时间差 | 系统标记日 vs 该商机进入公开榜单/媒体日的中位差值，按季跟踪 |

G1 只需 Wave 0 的手工数据就能验 —— **它是最早能证伪整套方法论的一道门**，
应该优先做。如果 5 个品类的剪刀差全落在同一档，那供给侧引擎（本系统最大的
差异化）就是废的，越早知道越好。
