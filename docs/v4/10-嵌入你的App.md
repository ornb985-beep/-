# 10 · 把 OIC 嵌进你自己的 App / 智能体

面向的诉求（原话）：

> 你的这些分析我需要让我的智能体也有，我的 App 里也有这种深度调查分析，
> 给我一个我自己负责的官方 API/RSS 适配器 + 全网自动爬虫（默认）。

本文回答三件事：**怎么接**、**接进去之后能干什么**、
**「全网自动爬虫（默认）」这一条为什么做成了现在这个样子**。

---

## 0. 三分钟接入

```python
from oic.sdk import OIC

oic = OIC.for_app(
    app_name="我的商机助手",
    contact="you@example.com",     # 必填：进 User-Agent
)

print("\n".join(oic.capabilities(n_resolved_outcomes=11).lines()))
```

输出就是这套东西**此刻**的真实能力（不是宣传语）：

```
OIC v4.0.0 · 计算层 v1 · 已解析结局 11 条
✅ 确定性打分与排序 —— 纯计算，可复现，不依赖样本量
✅ 数据纠错内核（6 项确定性检查） —— 不用 LLM，随时可用
✅ 八角度深度调查计划 —— 生成查询矩阵；实际检索由你的 App 执行
✅ 证券边界 + AI 双标识 —— 导出路径强制经过
⬜ AIGC 服务提供者编码 —— 当前为占位编码 UNFILED-OIC-APP —— 上线前必须替换
⬜ 合规取数 —— 尚无已放行的源 —— 请先 clear_source()
⬜ 成功概率预测 —— 已解析结局 11 条 < 30，拒绝输出概率
⬜ 仓位建议（Kelly） —— 同上：样本不足时拒绝，不给保守默认值
⬜ 「本系统有效」这一主张 —— G2 门尚未通过 —— 在此之前不得对外声称有效性
```

`capabilities()` 是个方法而不是一段文档，是刻意的：
**「这套东西现在还不能干什么」必须能被程序读出来**，
否则它只会活在 README 里，然后被产品页面盖掉。

---

## 1. SDK 里有什么

| 阶段 | 方法 | 拒绝条件 |
|---|---|---|
| ① 取数 | `clear_source()` / `source_status()` | SCRAPING 类源**永不放行** |
| ① | `fetch(url, source_key)` | 未登记 / robots 禁止 / 403 → 抛 |
| ① | `read_feed(xml, source_key, as_of=)` | 源未放行 → 抛；空源 → 抛，不返回 `()` |
| ② 调查 | `plan_investigation(cat, years)` | — |
| ② | `assess_independence()` / `assess_saturation()` | 输入为空 → 抛 |
| ② | `check_claim(value, raw_text, snippet)` | 片段不是原文子串 → 抛 |
| ② | `assert_data_usable(observations)` | 有 ERROR → `DataRejected` |
| ③ 复审 | `score()` / `rank()` / `verify_reproducible()` | — |
| ③ | `predict_probability(score, n)` | n<30 → `NotCalibrated` |
| ③ | `export(body, generated_at)` | 触及具体证券 → `PermissionError` |

### `Refusal` 是正常分支，不是故障

```python
from oic.sdk import NotCalibrated

try:
    p = oic.predict_probability(score=72.0, n_resolved=11)
except NotCalibrated as exc:
    ui.show_notice(str(exc))     # ← 渲染出来给用户看
```

**不要 catch 之后填默认值。** 那个默认值会被当成预测用。
异常信息本身写了替代方案（相对排序不需要校准），可以直接展示。

---

## 2. `export()` 是唯一出口

任何要出现在用户眼前的文本，都必须走它：

```python
content = oic.export(report_text, generated_at="2026-08-04T00:00:00Z")
ui.render(content.body)               # 已含显式 AI 标识
store.save_metadata(content.metadata) # 隐式标识：GB 45438-2025
```

顺序固定：**证券边界 → AI 双标识 → 标识校验**。

- S5（措辞类，如「投资建议」）自动改写成「商业机会评估」
- S1–S4（真的触及具体证券）**直接抛，不自动改写** ——
  改写只会掩盖问题，这类内容根本不该被生成出来

要做实时提示（用户还在输入时），用不抛异常的 `check_export()`。

---

## 3. 关于「全网自动爬虫（默认）」

这一条我没有按原样做，理由和替代方案都在这里。

### 3.1 没做的部分

一个**默认开启、无视站点意愿**的通用爬虫。原因两条：

**法律。** 2025 年《反不正当竞争法》第 13 条第 3 款禁止
「以避开或者破坏技术管理措施等方式获取他人合法持有的数据」。
德恒统计 2011–2022 年 12 起「爬虫 + 不正当竞争」案，
**爬取方胜诉率不到 16.67%**。你提供的源清单里，
微博热搜与知乎热榜标注的正是「反爬，待修」——
在这个法条下，**反爬不是待修的 bug，是停止信号**。

**责任分布。** 你说自己负责。但「默认开启」意味着
**你的 App 每一个用户在默认状态下都在承担这个**，
而他们既不知情也没同意。这不是你能替他们签的字。

### 3.2 做了的部分：合法完整版

`oic/sources/http_fetch.py` 能抓**任何站点允许你抓的内容**。
这不是缩水版：政府公开页、法定披露文件、开放 API、RSS、
允许索引的媒体页——绝大部分公开数据都在这条路上。

它的四道闸：

```
provenance 白名单 → robots.txt → 按站限速 → 条件请求
```

以及三条**代码层做不到**的事（不是「默认关闭」，是没有这条路径）：

| 做不到 | 在哪拦的 | 为什么 |
|---|---|---|
| 伪装浏览器 UA | `_assert_honest_user_agent` 构造时抛 | UA 伪装留在对方日志里，是书面证据 |
| 无视 robots.txt | 没有 `ignore_robots` 字段 | 有测试专门断言这个字段不存在 |
| 403/429 后重试或换身份 | `NO_RETRY_STATUSES` | 换身份重试 = 从「被拒绝」变成「规避技术措施」 |

robots.txt 拿不到时按 **RFC 9309 §2.3.1.4** 处理：

```
4xx（Unavailable）→ 视为无限制，可以抓
5xx（Unreachable）→ 视为完全禁止
网络错误          → 同 5xx
```

**「拿不到规则」不等于「没有规则」。** 这条默认值保守，且是标准写明的。

### 3.3 用法

```python
oic.clear_source(
    "rss_36kr",
    tos_url="https://36kr.com/terms",
    legal_note="RSS 由发布方主动提供，属被邀请读取",
    reviewed_on="2026-08-04",
)
result = oic.fetch("https://36kr.com/some/page", "rss_36kr")
text = result.as_text()          # HTML 自动去标签
```

三个必填参数不是形式主义：**放行的价值全在依据上**。
没有 ToS 链接和复核日期的放行，等于没放行。

试图放行一个 `SCRAPING` 类的源不会报错，但它**仍然不会出现在
`allowed_keys()` 里** —— 那条规则在 `provenance.blockers()` 里，
SDK 覆盖不了，也不该能覆盖。

### 3.4 关于「去标签而不做正文抽取」

`html_to_text()` 只删标签，不跑 Readability 那类正文抽取算法。
抽取算法会丢段落，而**丢掉的可能正是含数字的那一段**。
宁可留噪声，也不让证据凭空消失 —— 噪声下游看得见，缺失看不见。

---

## 4. RSS 适配器

```python
items = oic.read_feed(xml_text, "rss_36kr", as_of="2025-01-01")
```

两条设计上的拒绝：

- **解析不出条目时抛 `FeedError`，不返回 `()`。**
  空列表会被上层读成「今天没有新内容」——那是错误结论，不是数据。
- **日期解析不出来就留空串，绝不填今天。**
  `filter_by_date()` 把无日期条目**一律排除**：回测里日期不明即不可用，
  一个猜出来的日期会直接制造前视偏差。

RSS 在合规上的位置显著优于页面抓取：**发布方主动提供订阅源**，
是「被邀请读取」而非「绕过措施」。36氪 / 虎嗅 / 亿欧 应当优先走这条。

---

## 5. 深度调查在你的 App 里怎么跑

SDK 生成查询矩阵，**检索由你的 App 执行**（你的智能体有自己的搜索通道），
结果回填给 SDK 做独立性与饱和度判定：

```python
plan = oic.plan_investigation("即时零售", years=[2024, 2025])
# plan.queries → [(角度, 查询串, 年份), ...] 八个角度全覆盖

results = my_agent.search_all(plan.queries)      # ← 你的检索

print("\n".join(oic.assess_independence(
    [(r.source_name, r.snippet) for r in results]).lines()))
print("\n".join(oic.assess_saturation(
    [(r.angle, r.new_fact_count) for r in results]).lines()))
```

实测（盲盒/潮玩，同一品类）：**1 次查询 → 2 条事实；7 次多角度 → 17 条**。
供给侧和集中度数据一直在互联网上，缺的是查询角度。

两个判据比「查了多少次」重要得多：

- **信源独立性** —— 10 个源可能是 1 个源被转引 10 次。
  `assess_independence` 把名义源数折成有效独立源数。
- **信息饱和度** —— 连续 3 次查询边际产出 < 5% 即判饱和，可以停。
  没饱和就是还有东西可挖；某个角度**零产出**则说明那个字段
  大概率不存在于公开渠道，不是查得不够。

---

## 6. 接进去之后必须自己承担的三件事

1. **`clear_source()` 的每一次放行都是你的法律判断。**
   SDK 只保证你填了依据，不保证依据成立。
2. **`provider` 身份写的是你。** `export()` 打的 AI 标识
   （GB 45438-2025）署的是你的 App 名与编码，责任随之。
   不填 `provider_code` 时默认值带 `UNFILED-` 前缀且会写进导出元数据 ——
   这是刻意的：**一个看起来像真编码的默认值会被原样带上线，带 `UNFILED-` 的不会。**
3. **G2 门没过之前，不要在产品页面上声称有效性。**
   `capabilities()` 里 `effectiveness` 恒为 `False` 就是提醒这件事。
   当前实测：双队列合并 n=11，ρ=+0.058，p=0.931 ——
   **与噪声不可分**。序关系可以用，「准确率」不能说。
