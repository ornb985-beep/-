# 知识库索引

> **本文件由 `python -m oic.kb --index` 生成，请勿手改。**
> 手改的内容会在下次重建时被覆盖，而且不会有人发现。

共 **210** 条条目 · 现行 209 · 已被取代 0 · 已证伪 1 · 外部未验证 34

## 置信档位的含义

| 档位 | 含义 |
|---|---|
| ✅ CONFIRMED | 关于世界：A 级证据 + ≥2 独立源 + 样本 ≥30；关于本系统：A 级证据且已验证 |
| 🟢 SUPPORTED | 证据充分但未达上一档 |
| 🟡 PROVISIONAL | 单源，或样本不足 |
| ⬜ UNVERIFIED | 先验值，或外部来源 —— **本项目没有验证过** |
| ❌ FALSIFIED | 已被后续证据推翻。**保留在库里**，因为「为什么错」是知识 |

档位由 `(evidence_grade, n_independent_sources, sample_size, maturity)` 确定性推出，**不可手填**。

## GOV · 门禁 / 失效模式 / 回退规则（27 条）

| ID | 标题 | 类型 | 档位 | 备注 |
|---|---|---|---|---|
| [K-GOV-001](entries/verified/governance/K-GOV-001.md) | G0 可复现门：双跑逐字节一致 | criterion | ✅ CONFIRMED |  |
| [K-GOV-002](entries/verified/governance/K-GOV-002.md) | G1 区分度门：指标不得塌缩成同一档 | criterion | ⬜ UNVERIFIED |  |
| [K-GOV-003](entries/verified/governance/K-GOV-003.md) | G2 有效性门：BS < UNC 且样本 ≥30 | criterion | ⬜ UNVERIFIED |  |
| [K-GOV-004](entries/verified/governance/K-GOV-004.md) | G3 效率门：比人省 | criterion | ⬜ UNVERIFIED |  |
| [K-GOV-005](entries/verified/governance/K-GOV-005.md) | G4 时间差门：比公开榜单早 | criterion | ⬜ UNVERIFIED |  |
| [K-GOV-006](entries/verified/governance/K-GOV-006.md) | 没有 G0–G2，任何功能都只是更华丽的猜测 | criterion | ✅ CONFIRMED |  |
| [K-GOV-007](entries/verified/governance/K-GOV-007.md) | 失效模式1：地基未验证 —— C/O/D/E 四维从未被证明有预测力 | antipattern | ✅ CONFIRMED |  |
| [K-GOV-008](entries/verified/governance/K-GOV-008.md) | 失效模式2：Outcome 零条 → 七个模块空转 | antipattern | ✅ CONFIRMED |  |
| [K-GOV-009](entries/verified/governance/K-GOV-009.md) | 失效模式3：归因不可能 —— 赚钱是系统还是执行力 | antipattern | ✅ CONFIRMED |  |
| [K-GOV-010](entries/verified/governance/K-GOV-010.md) | 失效模式4：代理结局的 Goodhart 效应 | antipattern | 🟢 SUPPORTED |  |
| [K-GOV-011](entries/verified/governance/K-GOV-011.md) | 失效模式5：Kelly 在胜率未知时会主动伤人 | antipattern | ✅ CONFIRMED |  |
| [K-GOV-012](entries/verified/governance/K-GOV-012.md) | 失效模式6：数据源合法性可能整体崩塌 | antipattern | ✅ CONFIRMED |  |
| [K-GOV-013](entries/verified/governance/K-GOV-013.md) | 失效模式7：污染检测误报多于真报 | antipattern | 🟢 SUPPORTED |  |
| [K-GOV-014](entries/verified/governance/K-GOV-014.md) | 失效模式8：多 agent 可靠性乘法 | antipattern | ✅ CONFIRMED |  |
| [K-GOV-015](entries/verified/governance/K-GOV-015.md) | 失效模式9：LLM 判断层的天花板 = 普通人 | antipattern | ✅ CONFIRMED |  |
| [K-GOV-016](entries/verified/governance/K-GOV-016.md) | 失效模式10：同质化自噬只是被推迟 | antipattern | ⬜ UNVERIFIED |  |
| [K-GOV-017](entries/verified/governance/K-GOV-017.md) | 回退：多 agent 成本失控即退回单 agent | criterion | 🟢 SUPPORTED |  |
| [K-GOV-018](entries/verified/governance/K-GOV-018.md) | 回退：单 agent 基线 ≥45% 时不扩 agent | criterion | 🟢 SUPPORTED |  |
| [K-GOV-019](entries/verified/governance/K-GOV-019.md) | 回退：顺序推理任务一律不扩 agent | criterion | 🟢 SUPPORTED |  |
| [K-GOV-020](entries/verified/governance/K-GOV-020.md) | 回退：span 丢弃率过高改提示词不放宽校验 | criterion | 🟢 SUPPORTED |  |
| [K-GOV-021](entries/verified/governance/K-GOV-021.md) | 回退：重试率过高改 schema 不加重试 | criterion | 🟢 SUPPORTED |  |
| [K-GOV-022](entries/verified/governance/K-GOV-022.md) | 回退：剪刀差无区分度即停建采集层 | criterion | 🟢 SUPPORTED |  |
| [K-GOV-023](entries/verified/governance/K-GOV-023.md) | 回退：代理结局不过 Prentice 即停用 | criterion | 🟢 SUPPORTED |  |
| [K-GOV-024](entries/verified/governance/K-GOV-024.md) | 回退：污染检测误报多即保持关闭 | criterion | 🟢 SUPPORTED |  |
| [K-GOV-025](entries/verified/governance/K-GOV-025.md) | 回退：法务否决即删除能力不找替代爬取 | criterion | 🟢 SUPPORTED |  |
| [K-GOV-026](entries/verified/governance/K-GOV-026.md) | 这套设计能保证什么、不能保证什么 | fact | 🟢 SUPPORTED |  |
| [K-GOV-027](entries/verified/governance/K-GOV-027.md) | 现在不能说的六句话 | criterion | ✅ CONFIRMED |  |

## ORC · AI 调度体系（14 条）

| ID | 标题 | 类型 | 档位 | 备注 |
|---|---|---|---|---|
| [K-ORC-001](entries/verified/orchestration/K-ORC-001.md) | 铁律1：确定性计算与 LLM 判断物理隔离 | criterion | ✅ CONFIRMED |  |
| [K-ORC-002](entries/verified/orchestration/K-ORC-002.md) | 铁律2：没有实测基线，不准扩多智能体 | criterion | ✅ CONFIRMED |  |
| [K-ORC-003](entries/verified/orchestration/K-ORC-003.md) | 铁律3：挑战者必须有独立上下文 | criterion | 🟢 SUPPORTED |  |
| [K-ORC-004](entries/verified/orchestration/K-ORC-004.md) | 四级漏斗：不设限粗筛 → 零成本去重 → 分流 → 贵通道精查 | method | 🟢 SUPPORTED |  |
| [K-ORC-005](entries/verified/orchestration/K-ORC-005.md) | 低成本 AI 只能做归类，不能替代精查 | criterion | 🟢 SUPPORTED |  |
| [K-ORC-006](entries/verified/orchestration/K-ORC-006.md) | 价值分流：付不起就如实标未处理，不降标准 | criterion | 🟢 SUPPORTED |  |
| [K-ORC-007](entries/verified/orchestration/K-ORC-007.md) | 诚实计数：宁可报少，不许凑数 | criterion | 🟢 SUPPORTED |  |
| [K-ORC-008](entries/verified/orchestration/K-ORC-008.md) | 不限成本 ≠ 不计数 | criterion | 🟢 SUPPORTED |  |
| [K-ORC-009](entries/verified/orchestration/K-ORC-009.md) | 漏斗自洽性必须在启动时炸，而不是线上第 13 次 | method | ✅ CONFIRMED |  |
| [K-ORC-010](entries/verified/orchestration/K-ORC-010.md) | 输出前的三道强制闸门 | criterion | ✅ CONFIRMED |  |
| [K-ORC-011](entries/verified/orchestration/K-ORC-011.md) | 人机边界：模型不做终审 | criterion | 🟢 SUPPORTED |  |
| [K-ORC-012](entries/verified/orchestration/K-ORC-012.md) | SDK 把纪律一起打包，而不只是转发 import | method | ✅ CONFIRMED |  |
| [K-ORC-013](entries/verified/orchestration/K-ORC-013.md) | capabilities() 让「还不能干什么」可被程序读出 | method | ✅ CONFIRMED |  |
| [K-ORC-014](entries/verified/orchestration/K-ORC-014.md) | provider_code 缺省带 UNFILED- 前缀 | method | ✅ CONFIRMED |  |

## ACQ · 取数与源治理（26 条）

| ID | 标题 | 类型 | 档位 | 备注 |
|---|---|---|---|---|
| [K-ACQ-001](entries/verified/acquisition/K-ACQ-001.md) | 数据源白名单是采集层的唯一入口 | criterion | ✅ CONFIRMED |  |
| [K-ACQ-002](entries/verified/acquisition/K-ACQ-002.md) | SCRAPING 类源永不放行，法务放行也不行 | criterion | ✅ CONFIRMED |  |
| [K-ACQ-003](entries/verified/acquisition/K-ACQ-003.md) | 反爬是停止信号，不是待修的 bug | lesson | ✅ CONFIRMED |  |
| [K-ACQ-004](entries/verified/acquisition/K-ACQ-004.md) | 403/429 后不重试、不换 UA、不换 IP | criterion | ✅ CONFIRMED |  |
| [K-ACQ-005](entries/verified/acquisition/K-ACQ-005.md) | 取数器在代码层做不到伪装浏览器 UA | criterion | ✅ CONFIRMED |  |
| [K-ACQ-006](entries/verified/acquisition/K-ACQ-006.md) | 没有忽略 robots.txt 的开关 | criterion | ✅ CONFIRMED |  |
| [K-ACQ-007](entries/verified/acquisition/K-ACQ-007.md) | robots.txt 不可达时视为完全禁止 | criterion | ✅ CONFIRMED |  |
| [K-ACQ-008](entries/verified/acquisition/K-ACQ-008.md) | 站点声明的 Crawl-delay 只会让间隔变长 | criterion | ✅ CONFIRMED |  |
| [K-ACQ-009](entries/verified/acquisition/K-ACQ-009.md) | robots.txt 按 origin 缓存，不是每页都拉 | method | ✅ CONFIRMED |  |
| [K-ACQ-010](entries/verified/acquisition/K-ACQ-010.md) | 条件请求省对方流量也省自己的 | method | 🟢 SUPPORTED |  |
| [K-ACQ-011](entries/verified/acquisition/K-ACQ-011.md) | 解码失败抛错，绝不用 errors='replace' | criterion | ✅ CONFIRMED |  |
| [K-ACQ-012](entries/verified/acquisition/K-ACQ-012.md) | 超出大小上限时报错，不截断 | criterion | ✅ CONFIRMED |  |
| [K-ACQ-013](entries/verified/acquisition/K-ACQ-013.md) | HTML 只去标签，不做正文抽取 | criterion | ✅ CONFIRMED |  |
| [K-ACQ-014](entries/verified/acquisition/K-ACQ-014.md) | RSS 在合规上优于抓页面 | fact | 🟢 SUPPORTED |  |
| [K-ACQ-015](entries/verified/acquisition/K-ACQ-015.md) | 订阅源解析不出条目时抛错，不返回空列表 | criterion | ✅ CONFIRMED |  |
| [K-ACQ-016](entries/verified/acquisition/K-ACQ-016.md) | 日期解析不出来就留空，绝不填今天 | criterion | ✅ CONFIRMED |  |
| [K-ACQ-017](entries/verified/acquisition/K-ACQ-017.md) | 取数返回空内容时抛错，不当作「该文件无数据」 | criterion | 🟢 SUPPORTED |  |
| [K-ACQ-018](entries/verified/acquisition/K-ACQ-018.md) | 招股书是供给侧数据的最优公开来源 | fact | 🟢 SUPPORTED |  |
| [K-ACQ-019](entries/verified/acquisition/K-ACQ-019.md) | 中文招股书 PDF 的软换行不能当句末 | lesson | ✅ CONFIRMED |  |
| [K-ACQ-020](entries/verified/acquisition/K-ACQ-020.md) | 招股书章节标题必须是短行，否则会在正文里误匹配 | lesson | ✅ CONFIRMED |  |
| [K-ACQ-021](entries/verified/acquisition/K-ACQ-021.md) | PDF 的 CID 字体需要 ToUnicode CMap 才能正确提取 | lesson | 🟢 SUPPORTED |  |
| [K-ACQ-022](entries/verified/acquisition/K-ACQ-022.md) | 供给侧数据在公开渠道的可得性是结构性缺口 | fact | ✅ CONFIRMED |  |
| [K-ACQ-023](entries/verified/acquisition/K-ACQ-023.md) | 微博热搜与知乎热榜：登记为 SCRAPING，永不放行 | fact | 🟢 SUPPORTED |  |
| [K-ACQ-024](entries/verified/acquisition/K-ACQ-024.md) | 百度/头条/抖音热榜：可登记但需逐个法务放行 | fact | 🟢 SUPPORTED |  |
| [K-ACQ-025](entries/verified/acquisition/K-ACQ-025.md) | 国家统计局是 A 级来源 | fact | 🟢 SUPPORTED |  |
| [K-ACQ-026](entries/verified/acquisition/K-ACQ-026.md) | gsxt / 招投标 / SEC EDGAR / 巨潮：已登记的 A 级政府与法定披露源 | fact | 🟢 SUPPORTED |  |

## EVD · 证据核验（13 条）

| ID | 标题 | 类型 | 档位 | 备注 |
|---|---|---|---|---|
| [K-EVD-001](entries/verified/evidence/K-EVD-001.md) | 每个数字必须能用字符偏移回到原文 | criterion | ✅ CONFIRMED |  |
| [K-EVD-002](entries/verified/evidence/K-EVD-002.md) | 数值展开必须处理中文单位 | method | ✅ CONFIRMED |  |
| [K-EVD-003](entries/verified/evidence/K-EVD-003.md) | 我把「3.81万」记成 3,810,000 —— 100 倍单位错 | lesson | ✅ CONFIRMED |  |
| [K-EVD-004](entries/verified/evidence/K-EVD-004.md) | 双源锚定：有效独立源 <2 一律标待核实 | criterion | 🟢 SUPPORTED |  |
| [K-EVD-005](entries/verified/evidence/K-EVD-005.md) | 证据有时效，越旧权重越低 | method | 🟢 SUPPORTED |  |
| [K-EVD-006](entries/verified/evidence/K-EVD-006.md) | 真值发现：源可靠度与真值互相迭代 | method | 🟢 SUPPORTED |  |
| [K-EVD-007](entries/verified/evidence/K-EVD-007.md) | 证券闸误杀过真实 URL —— 且我当时声称过 0 误杀 | lesson | ✅ CONFIRMED |  |
| [K-EVD-008](entries/verified/evidence/K-EVD-008.md) | URL 掩码必须等长 | method | ✅ CONFIRMED |  |
| [K-EVD-009](entries/verified/evidence/K-EVD-009.md) | 证据分 A/B/C/D 四级 | method | 🟢 SUPPORTED |  |
| [K-EVD-010](entries/verified/evidence/K-EVD-010.md) | 检索摘要不是原文，中间多一层误差 | lesson | ✅ CONFIRMED |  |
| [K-EVD-011](entries/verified/evidence/K-EVD-011.md) | 只有预测值的数据一律排除 | criterion | ✅ CONFIRMED |  |
| [K-EVD-012](entries/verified/evidence/K-EVD-012.md) | 幸存者偏差：死掉的品类报道更少 | fact | 🟢 SUPPORTED |  |
| [K-EVD-013](entries/verified/evidence/K-EVD-013.md) | 我知道后续事实，这个偏差只能压制不能消除 | lesson | ✅ CONFIRMED |  |

## MET · 口径与时间闸（13 条）

| ID | 标题 | 类型 | 档位 | 备注 |
|---|---|---|---|---|
| [K-MET-001](entries/verified/metrics/K-MET-001.md) | 指标身份 = Family × Scope × Measure 三要素 | method | ✅ CONFIRMED |  |
| [K-MET-002](entries/verified/metrics/K-MET-002.md) | 存量与流量混淆会得出「新增大于存量」 | criterion | ✅ CONFIRMED |  |
| [K-MET-003](entries/verified/metrics/K-MET-003.md) | 跨 Scope 合并一律拒绝 | criterion | ✅ CONFIRMED |  |
| [K-MET-004](entries/verified/metrics/K-MET-004.md) | 市占率不是市场规模 | lesson | ✅ CONFIRMED |  |
| [K-MET-005](entries/verified/metrics/K-MET-005.md) | as-of 时间闸：未来信息进来直接抛错 | criterion | ✅ CONFIRMED |  |
| [K-MET-006](entries/verified/metrics/K-MET-006.md) | 增速在中文里带符号，比较必须取绝对值 | lesson | ✅ CONFIRMED |  |
| [K-MET-007](entries/verified/metrics/K-MET-007.md) | 增速自洽冲突时两个来源都不用 | criterion | ✅ CONFIRMED |  |
| [K-MET-008](entries/verified/metrics/K-MET-008.md) | 部分之和必须约等于整体 | criterion | 🟢 SUPPORTED |  |
| [K-MET-009](entries/verified/metrics/K-MET-009.md) | 异常值用 MAD 而不是标准差 | method | 🟢 SUPPORTED |  |
| [K-MET-010](entries/verified/metrics/K-MET-010.md) | audit 报 ERROR 的品类，下游拒绝使用 | criterion | ✅ CONFIRMED |  |
| [K-MET-011](entries/verified/metrics/K-MET-011.md) | 单位与币种必须先归一再比较 | method | ✅ CONFIRMED |  |
| [K-MET-012](entries/verified/metrics/K-MET-012.md) | E1/E2：样本池的排除与保留规则 | criterion | ✅ CONFIRMED |  |
| [K-MET-013](entries/verified/metrics/K-MET-013.md) | 第二轮采集的协议偏离已披露 | lesson | ✅ CONFIRMED |  |

## STA · 统计与防自欺（24 条）

| ID | 标题 | 类型 | 档位 | 备注 |
|---|---|---|---|---|
| [K-STA-001](entries/verified/statistics/K-STA-001.md) | 小样本用精确置换检验，不用正态近似 | method | ✅ CONFIRMED |  |
| [K-STA-002](entries/verified/statistics/K-STA-002.md) | Bootstrap 给区间，不给点值 | method | ✅ CONFIRMED |  |
| [K-STA-003](entries/verified/statistics/K-STA-003.md) | 先算运气基线，再看结果好不好看 | method | ✅ CONFIRMED |  |
| [K-STA-004](entries/verified/statistics/K-STA-004.md) | 多重检验必须做 Benjamini-Hochberg 校正 | method | 🟢 SUPPORTED |  |
| [K-STA-005](entries/verified/statistics/K-STA-005.md) | 回测过拟合概率 PBO 是必测项 | method | ✅ CONFIRMED |  |
| [K-STA-006](entries/verified/statistics/K-STA-006.md) | Purged / 留一交叉验证防止选特征与报成绩用同一批数据 | method | 🟢 SUPPORTED |  |
| [K-STA-007](entries/verified/statistics/K-STA-007.md) | Murphy 三分解：BS = REL − RES + UNC | method | ✅ CONFIRMED |  |
| [K-STA-008](entries/verified/statistics/K-STA-008.md) | 分箱损失必须单独报，不藏进残差 | lesson | ✅ CONFIRMED |  |
| [K-STA-009](entries/verified/statistics/K-STA-009.md) | ForecastBench：LLM 还没赢过人 | fact | 🟢 SUPPORTED |  |
| [K-STA-010](entries/verified/statistics/K-STA-010.md) | Kelly 用 Wilson 下界而非点估计 | method | ✅ CONFIRMED |  |
| [K-STA-011](entries/verified/statistics/K-STA-011.md) | ¼ Kelly 上限，且写进数据库 CHECK | parameter | ✅ CONFIRMED |  |
| [K-STA-012](entries/verified/statistics/K-STA-012.md) | 已解析结局 <30 时 Kelly 与概率一律拒绝输出 | criterion | ✅ CONFIRMED |  |
| [K-STA-013](entries/verified/statistics/K-STA-013.md) | 共形预测给带覆盖保证的区间 | method | 🟢 SUPPORTED |  |
| [K-STA-014](entries/verified/statistics/K-STA-014.md) | Beta-Binomial 分层借力解决冷启动 | method | 🟢 SUPPORTED |  |
| [K-STA-015](entries/verified/statistics/K-STA-015.md) | 代理结局必须过 Prentice 准则 | criterion | 🟢 SUPPORTED |  |
| [K-STA-016](entries/verified/statistics/K-STA-016.md) | 需求增速与结局的相关性与噪声不可分 | fact | 🟢 SUPPORTED |  |
| [K-STA-017](entries/verified/statistics/K-STA-017.md) | 我曾把 ρ=−0.289 过度解读成「方向值得记下来」 | lesson | ✅ CONFIRMED |  |
| [K-STA-018](entries/verified/statistics/K-STA-018.md) | 剪刀差方向转正但未达判据，且没打过运气基线 | fact | 🟢 SUPPORTED |  |
| [K-STA-019](entries/verified/statistics/K-STA-019.md) | 「品类在涨」≠「能赚钱」：8 个里打架 3 个 | fact | 🟢 SUPPORTED |  |
| [K-STA-020](entries/verified/statistics/K-STA-020.md) | 双标签：需求侧作副标签，商机侧作主标签 | criterion | ✅ CONFIRMED |  |
| [K-STA-021](entries/verified/statistics/K-STA-021.md) | 回测证明了管线通、防泄漏有效，没证明有效性 | fact | 🟢 SUPPORTED |  |
| [K-STA-022](entries/verified/statistics/K-STA-022.md) | 品类高度相关，有效样本量比 n 更小 | lesson | ✅ CONFIRMED |  |
| [K-STA-023](entries/verified/statistics/K-STA-023.md) | 来源冲突严重到无法完全消化 | fact | 🟢 SUPPORTED |  |
| [K-STA-024](entries/verified/statistics/K-STA-024.md) | 需求增速与结局呈弱负相关，方向值得记下来 | fact | ❌ FALSIFIED | 被 K-STA-016 推翻 |

## ANA · 商业分析引擎（28 条）

| ID | 标题 | 类型 | 档位 | 备注 |
|---|---|---|---|---|
| [K-ANA-001](entries/verified/analysis/K-ANA-001.md) | 主排序公式 | method | ✅ CONFIRMED |  |
| [K-ANA-002](entries/verified/analysis/K-ANA-002.md) | 红线一票归零，不可被高分抵消 | criterion | ✅ CONFIRMED |  |
| [K-ANA-003](entries/verified/analysis/K-ANA-003.md) | 红线 R1：已确认的合规问题 | criterion | 🟢 SUPPORTED |  |
| [K-ANA-004](entries/verified/analysis/K-ANA-004.md) | 红线 R2：绞肉机 | criterion | 🟢 SUPPORTED |  |
| [K-ANA-005](entries/verified/analysis/K-ANA-005.md) | 红线 R3：切换势能 ≤ 0 | criterion | 🟢 SUPPORTED |  |
| [K-ANA-006](entries/verified/analysis/K-ANA-006.md) | 红线 R4：高度集中且无差异化空间 | criterion | 🟢 SUPPORTED |  |
| [K-ANA-007](entries/verified/analysis/K-ANA-007.md) | 红线 R5：数据不可信 | criterion | 🟢 SUPPORTED |  |
| [K-ANA-008](entries/verified/analysis/K-ANA-008.md) | C/O/D/E 四维权重基准 25、上限 40 | parameter | ⬜ UNVERIFIED |  |
| [K-ANA-009](entries/verified/analysis/K-ANA-009.md) | 资源系数恒为 0.2，永不参与学习 | parameter | ✅ CONFIRMED |  |
| [K-ANA-010](entries/verified/analysis/K-ANA-010.md) | 剪刀差 M = 需求增速 − 供给增速 | method | 🟢 SUPPORTED |  |
| [K-ANA-011](entries/verified/analysis/K-ANA-011.md) | Schwartz 成熟度按同类企业数自动定级 | method | 🟢 SUPPORTED |  |
| [K-ANA-012](entries/verified/analysis/K-ANA-012.md) | 切换势能 = (推力+拉力) − (焦虑+惯性) | method | 🟢 SUPPORTED |  |
| [K-ANA-013](entries/verified/analysis/K-ANA-013.md) | Ulwick 机会分 = 重要性 + max(0, 重要性 − 满意度) | method | 🟢 SUPPORTED |  |
| [K-ANA-014](entries/verified/analysis/K-ANA-014.md) | Kano / Berger Better-Worse 系数 | method | 🟢 SUPPORTED |  |
| [K-ANA-015](entries/verified/analysis/K-ANA-015.md) | 禀赋效应：差异化必须可量化 | fact | 🟢 SUPPORTED |  |
| [K-ANA-016](entries/verified/analysis/K-ANA-016.md) | HHI 衡量竞争格局集中度 | method | ✅ CONFIRMED |  |
| [K-ANA-017](entries/verified/analysis/K-ANA-017.md) | 真实性系数下限 0.5，不允许单一代理打死商机 | parameter | ✅ CONFIRMED |  |
| [K-ANA-018](entries/verified/analysis/K-ANA-018.md) | 无供给侧证据时排序分封顶 0.6 | parameter | ✅ CONFIRMED |  |
| [K-ANA-019](entries/verified/analysis/K-ANA-019.md) | 变化率评分：趋势 60 + 幅度 20 + 形状 20 | lesson | ✅ CONFIRMED |  |
| [K-ANA-020](entries/verified/analysis/K-ANA-020.md) | 变化率分类与评分必须分开 | method | ✅ CONFIRMED |  |
| [K-ANA-021](entries/verified/analysis/K-ANA-021.md) | 八角度调查矩阵：缺哪个角度，字段就永远是空的 | method | ✅ CONFIRMED |  |
| [K-ANA-022](entries/verified/analysis/K-ANA-022.md) | 信源独立性：10 个源可能只是 1 个证据 | method | ✅ CONFIRMED |  |
| [K-ANA-023](entries/verified/analysis/K-ANA-023.md) | 信息饱和度：连续 3 次边际产出 <5% 即可停 | criterion | ✅ CONFIRMED |  |
| [K-ANA-024](entries/verified/analysis/K-ANA-024.md) | 零产出角度 = 数据不存在，不是查得不够 | criterion | ✅ CONFIRMED |  |
| [K-ANA-025](entries/verified/analysis/K-ANA-025.md) | 深度调查只查缺口角度，不重复已有字段 | method | 🟢 SUPPORTED |  |
| [K-ANA-026](entries/verified/analysis/K-ANA-026.md) | 盲区地图：完备不可达，但「知道缺什么」可达 | method | 🟢 SUPPORTED |  |
| [K-ANA-027](entries/verified/analysis/K-ANA-027.md) | logit-pooling 聚合多个概率意见 | method | 🟢 SUPPORTED |  |
| [K-ANA-028](entries/verified/analysis/K-ANA-028.md) | 概率粒度不宜过细 | criterion | 🟢 SUPPORTED |  |

## CMP · 法律与合规（21 条）

| ID | 标题 | 类型 | 档位 | 备注 |
|---|---|---|---|---|
| [K-CMP-001](entries/verified/compliance/K-CMP-001.md) | 证券边界的唯一判据：是否触及具体证券 | criterion | ✅ CONFIRMED |  |
| [K-CMP-002](entries/verified/compliance/K-CMP-002.md) | 证券边界 S1：出现具体证券代码 | criterion | ✅ CONFIRMED |  |
| [K-CMP-003](entries/verified/compliance/K-CMP-003.md) | 证券边界 S2：推荐具体证券买卖 | criterion | ✅ CONFIRMED |  |
| [K-CMP-004](entries/verified/compliance/K-CMP-004.md) | 证券边界 S3：给出买卖时机 | criterion | ✅ CONFIRMED |  |
| [K-CMP-005](entries/verified/compliance/K-CMP-005.md) | 证券边界 S4：预测证券价格走势 | criterion | ✅ CONFIRMED |  |
| [K-CMP-006](entries/verified/compliance/K-CMP-006.md) | 证券边界 S5：高危措辞自动改写 | method | ✅ CONFIRMED |  |
| [K-CMP-007](entries/verified/compliance/K-CMP-007.md) | 关键豁免：纯信息汇总不属于荐股软件 | fact | 🟢 SUPPORTED |  |
| [K-CMP-008](entries/verified/compliance/K-CMP-008.md) | 证券违规的罚则量级 | fact | 🟢 SUPPORTED |  |
| [K-CMP-009](entries/verified/compliance/K-CMP-009.md) | AI 内容必须同时有显式与隐式标识 | criterion | ✅ CONFIRMED |  |
| [K-CMP-010](entries/verified/compliance/K-CMP-010.md) | 内容编号必须确定性 | criterion | ✅ CONFIRMED |  |
| [K-CMP-011](entries/verified/compliance/K-CMP-011.md) | provider_code 应填真实算法备案号 | criterion | ✅ CONFIRMED |  |
| [K-CMP-012](entries/verified/compliance/K-CMP-012.md) | PIPL：处理个人信息需要 PIPIA | criterion | 🟢 SUPPORTED |  |
| [K-CMP-013](entries/verified/compliance/K-CMP-013.md) | 审计日志只可追加 | criterion | 🟢 SUPPORTED |  |
| [K-CMP-014](entries/verified/compliance/K-CMP-014.md) | 预测一旦写入不可修改 | criterion | 🟢 SUPPORTED |  |
| [K-CMP-015](entries/verified/compliance/K-CMP-015.md) | 计算层版本号变更即隔离历史预测 | criterion | ✅ CONFIRMED |  |
| [K-CMP-016](entries/verified/compliance/K-CMP-016.md) | 多租户用行级安全隔离 | method | 🟢 SUPPORTED |  |
| [K-CMP-017](entries/verified/compliance/K-CMP-017.md) | 假设必须可证伪才允许写入 | criterion | 🟢 SUPPORTED |  |
| [K-CMP-018](entries/verified/compliance/K-CMP-018.md) | 基础率来源不得为空 | criterion | 🟢 SUPPORTED |  |
| [K-CMP-019](entries/verified/compliance/K-CMP-019.md) | 影子权重晋升必须有 Outcome 背书 | criterion | 🟢 SUPPORTED |  |
| [K-CMP-020](entries/verified/compliance/K-CMP-020.md) | 爬取禁令同时写进数据库 CHECK | criterion | ✅ CONFIRMED |  |
| [K-CMP-021](entries/verified/compliance/K-CMP-021.md) | 输出路径上的三道闸 | criterion | ✅ CONFIRMED |  |

## DLV · 交付物（10 条）

| ID | 标题 | 类型 | 档位 | 备注 |
|---|---|---|---|---|
| [K-DLV-001](entries/verified/delivery/K-DLV-001.md) | BP 里每条论证都挂着可追溯证据 | criterion | 🟢 SUPPORTED |  |
| [K-DLV-002](entries/verified/delivery/K-DLV-002.md) | 90 天四阶段，每阶段带量化止损门槛 | method | 🟢 SUPPORTED |  |
| [K-DLV-003](entries/verified/delivery/K-DLV-003.md) | 「可预测的结果」写成条件区间 + 反证条件 | criterion | ✅ CONFIRMED |  |
| [K-DLV-004](entries/verified/delivery/K-DLV-004.md) | 反证条件必须在 14 天内可判定 | criterion | 🟢 SUPPORTED |  |
| [K-DLV-005](entries/verified/delivery/K-DLV-005.md) | 资源规划给三技能模型缺口，不给岗位名称 | method | 🟢 SUPPORTED |  |
| [K-DLV-006](entries/verified/delivery/K-DLV-006.md) | 资金按阶段给上限，不给总预算 | method | 🟢 SUPPORTED |  |
| [K-DLV-007](entries/verified/delivery/K-DLV-007.md) | 平台动作要具体到「在哪做什么」 | method | 🟡 PROVISIONAL |  |
| [K-DLV-008](entries/verified/delivery/K-DLV-008.md) | Outcome 是系统命门 | fact | 🟢 SUPPORTED |  |
| [K-DLV-009](entries/verified/delivery/K-DLV-009.md) | 拒绝输出是正常分支，应当渲染给用户看 | criterion | ✅ CONFIRMED |  |
| [K-DLV-010](entries/verified/delivery/K-DLV-010.md) | top3 而不是全量排序 | method | 🟢 SUPPORTED |  |

## EXT · 通用 AI 方法论（本项目未验证）（34 条）

> ⚠️ **这一区没有我们自己的验证。** 校验器强制它们不得单独支撑任何已验证结论。

| ID | 标题 | 类型 | 档位 | 备注 |
|---|---|---|---|---|
| [K-EXT-001](entries/external/K-EXT-001.md) | 结构化输出优于自由文本解析 | method | ⬜ UNVERIFIED |  |
| [K-EXT-002](entries/external/K-EXT-002.md) | 检索增强（RAG）把知识与参数解耦 | method | ⬜ UNVERIFIED |  |
| [K-EXT-003](entries/external/K-EXT-003.md) | 上下文工程比提示词技巧更重要 | method | ⬜ UNVERIFIED |  |
| [K-EXT-004](entries/external/K-EXT-004.md) | 提示缓存能大幅降低重复前缀的成本 | method | ⬜ UNVERIFIED |  |
| [K-EXT-005](entries/external/K-EXT-005.md) | 批处理适合可容忍延迟的大规模任务 | method | ⬜ UNVERIFIED |  |
| [K-EXT-006](entries/external/K-EXT-006.md) | 小模型做路由，大模型做判断 | method | ⬜ UNVERIFIED |  |
| [K-EXT-007](entries/external/K-EXT-007.md) | Self-consistency：多次采样取众数 | method | ⬜ UNVERIFIED |  |
| [K-EXT-008](entries/external/K-EXT-008.md) | 思维链在复杂推理上有效，在简单任务上可能有害 | method | ⬜ UNVERIFIED |  |
| [K-EXT-009](entries/external/K-EXT-009.md) | LLM-as-judge 需要独立评审与人工锚定 | method | ⬜ UNVERIFIED |  |
| [K-EXT-010](entries/external/K-EXT-010.md) | Agent 应当有明确的终止条件与迭代上限 | method | ⬜ UNVERIFIED |  |
| [K-EXT-011](entries/external/K-EXT-011.md) | 工具定义的质量决定 agent 的上限 | method | ⬜ UNVERIFIED |  |
| [K-EXT-012](entries/external/K-EXT-012.md) | 错误消息应当告诉 agent 下一步怎么做 | method | ⬜ UNVERIFIED |  |
| [K-EXT-013](entries/external/K-EXT-013.md) | 微调适合调整风格与格式，不适合注入知识 | method | ⬜ UNVERIFIED |  |
| [K-EXT-014](entries/external/K-EXT-014.md) | 评测集必须与训练/调优过程隔离 | method | ⬜ UNVERIFIED |  |
| [K-EXT-015](entries/external/K-EXT-015.md) | 生产环境需要记录完整的输入输出以便回溯 | method | ⬜ UNVERIFIED |  |
| [K-EXT-016](entries/external/K-EXT-016.md) | 流式输出改善体感但不改善质量 | method | ⬜ UNVERIFIED |  |
| [K-EXT-017](entries/external/K-EXT-017.md) | 温度调低不等于更可靠 | method | ⬜ UNVERIFIED |  |
| [K-EXT-018](entries/external/K-EXT-018.md) | 长上下文不等于可以省掉检索 | method | ⬜ UNVERIFIED |  |
| [K-EXT-019](entries/external/K-EXT-019.md) | 模型版本升级需要重跑评测而不是假设更好 | method | ⬜ UNVERIFIED |  |
| [K-EXT-020](entries/external/K-EXT-020.md) | 幻觉率随任务熟悉度下降而上升 | fact | ⬜ UNVERIFIED |  |
| [K-EXT-021](entries/external/K-EXT-021.md) | 数值计算不应交给语言模型 | criterion | ⬜ UNVERIFIED |  |
| [K-EXT-022](entries/external/K-EXT-022.md) | 引用必须可验证，否则等于没有引用 | criterion | ⬜ UNVERIFIED |  |
| [K-EXT-023](entries/external/K-EXT-023.md) | 多轮对话的上下文需要主动管理 | method | ⬜ UNVERIFIED |  |
| [K-EXT-024](entries/external/K-EXT-024.md) | 护栏应当在输入与输出两侧都做 | method | ⬜ UNVERIFIED |  |
| [K-EXT-025](entries/external/K-EXT-025.md) | 确定性种子不能保证 LLM 输出可复现 | fact | ⬜ UNVERIFIED |  |
| [K-EXT-026](entries/external/K-EXT-026.md) | 成本估算要按 token 而不是按请求 | parameter | ⬜ UNVERIFIED |  |
| [K-EXT-027](entries/external/K-EXT-027.md) | 对抗样本应当来自真实失败而非人工构造 | method | ⬜ UNVERIFIED |  |
| [K-EXT-028](entries/external/K-EXT-028.md) | 增量式采纳：先只读，再建议，最后自动执行 | criterion | ⬜ UNVERIFIED |  |
| [K-EXT-029](entries/external/K-EXT-029.md) | 人在回路的位置比人在回路本身重要 | method | ⬜ UNVERIFIED |  |
| [K-EXT-030](entries/external/K-EXT-030.md) | 模型输出的自信程度与正确性关联很弱 | fact | ⬜ UNVERIFIED |  |
| [K-EXT-031](entries/external/K-EXT-031.md) | 检索的召回比精度更值得优先优化 | method | ⬜ UNVERIFIED |  |
| [K-EXT-032](entries/external/K-EXT-032.md) | 向量检索与关键词检索应当混合 | method | ⬜ UNVERIFIED |  |
| [K-EXT-033](entries/external/K-EXT-033.md) | 同一提示词在不同模型上的表现不可迁移 | lesson | ⬜ UNVERIFIED |  |
| [K-EXT-034](entries/external/K-EXT-034.md) | 失败要快且可见，不要静默降级 | criterion | ⬜ UNVERIFIED |  |

## 已证伪清单（刻意保留）

**被推翻的结论是资产。** 它记录了我们曾经怎么想、被什么推翻、以及那次教训。删掉它等于让同一个错误可以再犯一次。

- **K-STA-024** 需求增速与结局呈弱负相关，方向值得记下来 → 被 `K-STA-016` 推翻

