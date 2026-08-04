"""指标口径分类法 —— 判断两个数字能不能放在一起比。

侦察时实测到的三组数字，说明为什么必须有这一层：

    露营"核心市场规模 1334 亿" vs 露营"装备市场规模 226.94 亿"
        → 不是偏差 488%，是两个不同指标。平均它们等于制造假数据。

    露营"2022 新注册 330 万家" vs 露营"存量超 100 万家"
        → 新增 > 存量，自相矛盾。因为一个是 flow 一个是 stock。

    预制菜"B端 4200 亿" + "C端 1973 亿" vs "整体 6173 亿"
        → 这三个能对上（4200+1973=6173），说明口径自洽；
          但如果把 B 端和整体当同一指标去平均，就毁了。

所以：**口径不同 → 拒绝合并**，而不是当成偏差去降权。
现有的 ``evidence/decay.py::anchor`` 只会做数值降权，那是不够的。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


class Family:
    """指标大类 —— 量纲不同，绝不可跨类比较。"""

    MARKET_SIZE = "market_size"       # 币种金额
    COMPANY_COUNT = "company_count"   # 家数
    GROWTH_RATE = "growth_rate"       # 百分数
    STORE_COUNT = "store_count"       # 门店数
    USER_COUNT = "user_count"         # 人数
    FUNDING = "funding"               # 融资额


class Scope:
    """口径限定 —— 同一大类下的不同切法。"""

    ALL = "all"                 # 整体
    CORE = "core"               # 核心市场（不含带动）
    DRIVEN = "driven"           # 带动市场（含上下游，通常大得多）
    EQUIPMENT = "equipment"     # 装备/器材
    RETAIL = "retail"           # 零售额
    B2B = "b2b"
    B2C = "b2c"


class Measure:
    """存量还是流量 —— 混淆这个会得出"新增大于存量"的荒谬结论。"""

    STOCK = "stock"     # 时点存量：存续企业数、市场规模
    FLOW = "flow"       # 期间流量：新增注册数、注销数、当年融资额


@dataclass(frozen=True)
class MetricKey:
    """指标的完整身份。四要素全等才允许合并。"""

    family: str
    scope: str
    measure: str

    def __post_init__(self) -> None:
        valid_families = {v for k, v in vars(Family).items() if not k.startswith("_")}
        valid_scopes = {v for k, v in vars(Scope).items() if not k.startswith("_")}
        valid_measures = {v for k, v in vars(Measure).items() if not k.startswith("_")}
        if self.family not in valid_families:
            raise ValueError(f"未知 family: {self.family}")
        if self.scope not in valid_scopes:
            raise ValueError(f"未知 scope: {self.scope}")
        if self.measure not in valid_measures:
            raise ValueError(f"未知 measure: {self.measure}")

    def mergeable_with(self, other: "MetricKey") -> bool:
        return (self.family, self.scope, self.measure) == (
            other.family, other.scope, other.measure
        )

    def label(self) -> str:
        return f"{self.family}/{self.scope}/{self.measure}"


class MetricConflict(ValueError):
    """试图合并口径不同的观测。"""


def assert_mergeable(keys: "list[MetricKey]") -> MetricKey:
    """全部同口径才放行，否则抛错并说清差在哪。"""
    if not keys:
        raise ValueError("观测为空")
    first = keys[0]
    for key in keys[1:]:
        if not first.mergeable_with(key):
            raise MetricConflict(
                f"口径不同，拒绝合并：{first.label()} vs {key.label()}。\n"
                "这不是数值偏差，是两个不同的指标 —— 平均它们等于制造假数据。\n"
                "正确做法：分开报，或先明确要用哪个口径。"
            )
    return first


# ---------------------------------------------------------------------------
# 常用口径的快捷构造
# ---------------------------------------------------------------------------

MARKET_SIZE_ALL = MetricKey(Family.MARKET_SIZE, Scope.ALL, Measure.STOCK)
MARKET_SIZE_CORE = MetricKey(Family.MARKET_SIZE, Scope.CORE, Measure.STOCK)
MARKET_SIZE_DRIVEN = MetricKey(Family.MARKET_SIZE, Scope.DRIVEN, Measure.STOCK)
MARKET_SIZE_EQUIPMENT = MetricKey(Family.MARKET_SIZE, Scope.EQUIPMENT, Measure.STOCK)
MARKET_SIZE_RETAIL = MetricKey(Family.MARKET_SIZE, Scope.RETAIL, Measure.STOCK)

#: 存续企业数（时点存量）
COMPANY_STOCK = MetricKey(Family.COMPANY_COUNT, Scope.ALL, Measure.STOCK)
#: 新增注册企业数（期间流量）
COMPANY_NEW = MetricKey(Family.COMPANY_COUNT, Scope.ALL, Measure.FLOW)

DEMAND_GROWTH = MetricKey(Family.GROWTH_RATE, Scope.ALL, Measure.FLOW)
SUPPLY_GROWTH = MetricKey(Family.GROWTH_RATE, Scope.ALL, Measure.FLOW)


#: 中文表述 → 口径。用于把检索到的文字标准化。
#: 长词在前，避免"市场规模"吃掉"核心市场规模"。
PHRASE_TO_KEY: tuple[tuple[str, MetricKey], ...] = (
    ("核心市场规模", MARKET_SIZE_CORE),
    ("带动市场规模", MARKET_SIZE_DRIVEN),
    ("装备市场规模", MARKET_SIZE_EQUIPMENT),
    ("用品市场规模", MARKET_SIZE_EQUIPMENT),
    ("零售额", MARKET_SIZE_RETAIL),
    ("零售规模", MARKET_SIZE_RETAIL),
    ("B端市场规模", MetricKey(Family.MARKET_SIZE, Scope.B2B, Measure.STOCK)),
    ("C端市场规模", MetricKey(Family.MARKET_SIZE, Scope.B2C, Measure.STOCK)),
    ("市场规模", MARKET_SIZE_ALL),
    ("新增注册", COMPANY_NEW),
    ("新注册", COMPANY_NEW),
    ("注册量", COMPANY_NEW),
    ("存续企业", COMPANY_STOCK),
    ("相关企业", COMPANY_STOCK),
    ("企业数量", COMPANY_STOCK),
    ("门店数", MetricKey(Family.STORE_COUNT, Scope.ALL, Measure.STOCK)),
    ("融资总额", MetricKey(Family.FUNDING, Scope.ALL, Measure.FLOW)),
)


def classify(phrase: str) -> MetricKey | None:
    """把中文指标名映射到口径。认不出返回 None —— **不猜**。"""
    for needle, key in PHRASE_TO_KEY:
        if needle in phrase:
            return key
    return None


def explain_conflict(a: MetricKey, b: MetricKey) -> str:
    """给人看的冲突说明。"""
    diffs = []
    if a.family != b.family:
        diffs.append(f"大类不同（{a.family} vs {b.family}）—— 量纲都不一样")
    if a.scope != b.scope:
        diffs.append(f"口径不同（{a.scope} vs {b.scope}）")
    if a.measure != b.measure:
        diffs.append(
            f"存量/流量不同（{a.measure} vs {b.measure}）"
            " —— 这类混淆会得出「新增大于存量」的荒谬结论"
        )
    return "；".join(diffs) if diffs else "无冲突"
