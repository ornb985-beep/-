"""深度多方调查 —— 对入围商机做穷尽式取证。

## 这个模块解决什么

单次查询拿到的是"某个来源碰巧提到的那几个数字"。
实测对比（盲盒/潮玩，同一品类）：

    1 次查询：只拿到需求增速代理（泡泡玛特营收 +2.8%）
    4 次多角度查询：企业存量 2600、新增序列 300→1470、
                    CR5 24%、龙头份额 12%、市场规模 478亿、融资 35 起

**供给侧和集中度数据一直在互联网上，是查询角度不够。**

## 但"多方"不等于"多个源"

真正决定准确率的是两件事，都可以测：

    信源独立性  10 个源可能是 1 个源被转引 10 次
    信息饱和度  新查询不再带来新事实 = 该挖的挖完了

本模块把这两个量化，让"信息充分"从感觉变成判据。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from oic.research import metrics as mx

# ---------------------------------------------------------------------------
# 查询矩阵
# ---------------------------------------------------------------------------

#: 调查角度 —— 每个角度对应一类无法互相替代的证据。
#: 缺哪个角度，对应的字段就永远是空的。
class Angle:
    DEMAND_SIZE = "demand_size"           # 市场规模与增速
    SUPPLY_ENTRY = "supply_entry"         # 企业新增注册
    SUPPLY_EXIT = "supply_exit"           # 注销吊销、闭店、退出
    CONCENTRATION = "concentration"       # CR5 / 市占率 / 竞争格局
    CAPITAL = "capital"                   # 融资数量与金额
    PROFITABILITY = "profitability"       # 毛利率、价格战、亏损
    CHANNEL = "channel"                   # 门店数、渠道结构
    REGULATION = "regulation"             # 政策、监管事件


#: 角度 → 它能填上的指标口径。用于算覆盖率。
ANGLE_FILLS: Mapping[str, tuple[mx.MetricKey, ...]] = {
    Angle.DEMAND_SIZE: (mx.MARKET_SIZE_ALL, mx.DEMAND_GROWTH),
    Angle.SUPPLY_ENTRY: (mx.COMPANY_NEW, mx.COMPANY_STOCK),
    Angle.SUPPLY_EXIT: (mx.COMPANY_STOCK,),
    Angle.CONCENTRATION: (mx.MARKET_SHARE_CR5, mx.MARKET_SHARE_SELF),
    Angle.CAPITAL: (mx.MetricKey(mx.Family.FUNDING, mx.Scope.ALL, mx.Measure.FLOW),),
    Angle.CHANNEL: (mx.MetricKey(mx.Family.STORE_COUNT, mx.Scope.ALL, mx.Measure.STOCK),),
    Angle.PROFITABILITY: (),
    Angle.REGULATION: (),
}

#: 每个角度的查询模板。``{cat}`` 品类名，``{year}`` 年份。
QUERY_TEMPLATES: Mapping[str, tuple[str, ...]] = {
    Angle.DEMAND_SIZE: (
        "{cat} {year}年 市场规模 亿元 同比增长",
        "{cat} 行业 {year} 规模 增速 报告",
    ),
    Angle.SUPPLY_ENTRY: (
        "{cat} 相关企业 {year} 新增注册量 企查查 天眼查 家",
        "{cat} 企业数量 {year} 存量 新成立 同比",
    ),
    Angle.SUPPLY_EXIT: (
        "{cat} {year} 注销 吊销 闭店 退出 倒闭 数量",
        "{cat} {year} 关店 收缩 撤出",
    ),
    Angle.CONCENTRATION: (
        "{cat} 市场集中度 CR5 竞争格局 {year} 市场份额 百分比",
        "{cat} {year} 龙头 市占率 行业格局 分散",
    ),
    Angle.CAPITAL: (
        "{cat} {year} 融资 事件 数量 金额 亿元",
        "{cat} 投融资 {year} 盘点 获投",
    ),
    Angle.PROFITABILITY: (
        "{cat} {year} 毛利率 净利润 价格战 亏损",
        "{cat} {year} 增收不增利 单店模型",
    ),
    Angle.CHANNEL: (
        "{cat} {year} 门店数量 万家 扩张",
    ),
    Angle.REGULATION: (
        "{cat} {year} 政策 监管 新规 影响",
    ),
}


def build_query_matrix(
    category: str, years: Sequence[int], angles: Sequence[str] | None = None
) -> tuple[tuple[str, str, int], ...]:
    """生成 (角度, 查询串, 年份) 的完整矩阵。

    刻意穷举而非精选：**漏掉一个角度，对应字段就永远是空的**，
    而多查一次的成本远低于永久性的数据缺口。
    """
    chosen = tuple(angles) if angles else tuple(QUERY_TEMPLATES)
    out: list[tuple[str, str, int]] = []
    for angle in chosen:
        if angle not in QUERY_TEMPLATES:
            raise ValueError(f"未知调查角度: {angle}")
        for template in QUERY_TEMPLATES[angle]:
            for year in years:
                out.append((angle, template.format(cat=category, year=year), year))
    return tuple(out)


# ---------------------------------------------------------------------------
# 信源独立性
# ---------------------------------------------------------------------------

#: 已知的一级数据供应商。大量二手报道都转引它们 ——
#: 十篇引用同一家的报道，独立性是 1 不是 10。
KNOWN_ORIGINATORS: Mapping[str, str] = {
    "企查查": "qcc", "天眼查": "tianyancha", "企业预警通": "qyyjt",
    "艾媒": "iimedia", "iiMedia": "iimedia",
    "前瞻": "qianzhan", "观研": "guanyan",
    "蝉妈妈": "chanmama", "飞瓜": "feigua",
    "国家统计局": "stats_gov", "中国连锁经营协会": "ccfa", "CCFA": "ccfa",
    "弗若斯特沙利文": "frost", "沙利文": "frost",
}


@dataclass(frozen=True)
class SourceNode:
    """一条证据的来源，含它自称的上游。"""

    source_name: str
    snippet: str = ""

    def originator(self) -> str:
        """从原文里识别它转引的一级源。识别不出返回自身。"""
        for phrase, key in KNOWN_ORIGINATORS.items():
            if phrase in self.snippet or phrase in self.source_name:
                return key
        return self.source_name


@dataclass(frozen=True)
class IndependenceReport:
    n_sources: int
    n_effective: int
    originator_groups: tuple[tuple[str, tuple[str, ...]], ...]
    anchored: bool

    @property
    def inflation(self) -> float:
        """名义源数 / 有效独立源数。>1 说明存在转引放大。"""
        return self.n_sources / self.n_effective if self.n_effective else float("inf")

    def lines(self) -> tuple[str, ...]:
        out = [f"名义来源 {self.n_sources} 个 → "
               f"**有效独立源 {self.n_effective} 个**"
               f"（转引放大 {self.inflation:.1f}×）"]
        for origin, members in self.originator_groups:
            if len(members) > 1:
                out.append(f"  ⚠️ {len(members)} 个来源同溯至「{origin}」：{'、'.join(members)}")
        if not self.anchored:
            out.append("  🔴 有效独立源 < 2，按双源锚定规则标「待核实」")
        return tuple(out)


def assess_independence(nodes: Sequence[SourceNode],
                        min_independent: int = 2) -> IndependenceReport:
    """把"几个来源"折算成"几个真正独立的来源"。

    这是「多方查询」能否提高准确率的分水岭：
    如果 10 个源都转引艾媒同一份报告，那不是 10 个证据，是 1 个。
    """
    if not nodes:
        raise ValueError("来源为空")

    groups: dict[str, list[str]] = {}
    for node in nodes:
        groups.setdefault(node.originator(), []).append(node.source_name)

    ordered = tuple(
        (origin, tuple(sorted(set(members))))
        for origin, members in sorted(groups.items())
    )
    effective = len(ordered)
    return IndependenceReport(
        n_sources=len(nodes), n_effective=effective,
        originator_groups=ordered, anchored=effective >= min_independent,
    )


# ---------------------------------------------------------------------------
# 信息饱和度
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SaturationPoint:
    query_index: int
    angle: str
    new_facts: int
    cumulative_facts: int

    @property
    def marginal_yield(self) -> float:
        return self.new_facts / max(self.cumulative_facts, 1)


@dataclass(frozen=True)
class SaturationReport:
    points: tuple[SaturationPoint, ...]
    total_facts: int
    saturated: bool
    saturation_index: int | None
    angles_covered: tuple[str, ...]
    angles_empty: tuple[str, ...]

    def lines(self) -> tuple[str, ...]:
        out = [f"共 {len(self.points)} 次查询，累计 {self.total_facts} 条已验证事实"]
        for p in self.points:
            out.append(f"  #{p.query_index} [{p.angle:<14}] +{p.new_facts} 条"
                       f"（累计 {p.cumulative_facts}，边际 {p.marginal_yield:.0%}）")
        if self.saturated:
            out.append(f"✅ 第 {self.saturation_index} 次查询后达到饱和 —— 可以停")
        else:
            out.append("⬜ 尚未饱和，继续查还能拿到新事实")
        if self.angles_empty:
            out.append(f"🔴 零产出角度：{'、'.join(self.angles_empty)}"
                       " —— 这些字段大概率不存在于公开渠道，不是查得不够")
        return tuple(out)


#: 连续这么多次查询的边际产出低于阈值，即判为饱和
SATURATION_WINDOW = 3
SATURATION_THRESHOLD = 0.05


def assess_saturation(
    yields: Sequence[tuple[str, int]],
    window: int = SATURATION_WINDOW,
    threshold: float = SATURATION_THRESHOLD,
) -> SaturationReport:
    """``yields`` 是按查询顺序的 (角度, 本次新增已验证事实数)。

    饱和的操作性定义：连续 ``window`` 次查询的边际产出都低于 ``threshold``。
    这把"信息够不够"从感觉变成判据。
    """
    if not yields:
        raise ValueError("查询记录为空")

    points: list[SaturationPoint] = []
    cumulative = 0
    for i, (angle, new_facts) in enumerate(yields, start=1):
        if new_facts < 0:
            raise ValueError("新增事实数不能为负")
        cumulative += new_facts
        points.append(SaturationPoint(i, angle, new_facts, cumulative))

    saturation_index: int | None = None
    for i in range(len(points) - window + 1):
        chunk = points[i:i + window]
        if all(p.marginal_yield < threshold for p in chunk):
            saturation_index = chunk[0].query_index
            break

    by_angle: dict[str, int] = {}
    for angle, new_facts in yields:
        by_angle[angle] = by_angle.get(angle, 0) + new_facts

    covered = tuple(sorted(a for a, n in by_angle.items() if n > 0))
    empty = tuple(sorted(a for a, n in by_angle.items() if n == 0))

    return SaturationReport(
        points=tuple(points), total_facts=cumulative,
        saturated=saturation_index is not None,
        saturation_index=saturation_index,
        angles_covered=covered, angles_empty=empty,
    )


# ---------------------------------------------------------------------------
# 调查计划
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InvestigationPlan:
    category: str
    queries: tuple[tuple[str, str, int], ...]
    missing_angles: tuple[str, ...]

    def lines(self) -> tuple[str, ...]:
        out = [f"【{self.category}】深度调查计划：{len(self.queries)} 条查询"]
        by_angle: dict[str, int] = {}
        for angle, _, _ in self.queries:
            by_angle[angle] = by_angle.get(angle, 0) + 1
        out.extend(f"  {angle:<14} {n} 条" for angle, n in sorted(by_angle.items()))
        if self.missing_angles:
            out.append(f"  当前缺口角度：{'、'.join(self.missing_angles)}")
        return tuple(out)


def plan_investigation(
    category: str,
    years: Sequence[int],
    已有指标: Iterable[mx.MetricKey] = (),
) -> InvestigationPlan:
    """按当前已有指标，只查还缺的角度。

    已经拿到的字段不重复查 —— 深度调查的成本应当花在缺口上。
    """
    have = set(已有指标)
    missing: list[str] = []
    for angle, fills in ANGLE_FILLS.items():
        if not fills:
            missing.append(angle)          # 无法用指标判断覆盖的角度，一律查
        elif not have.intersection(fills):
            missing.append(angle)

    queries = build_query_matrix(category, years, sorted(missing))
    return InvestigationPlan(category, queries, tuple(sorted(missing)))
