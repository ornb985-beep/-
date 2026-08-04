"""CODE 四维评分、资源匹配度、变现系数。

公式（v3 第三部分，原样保留）：
    需求强度 = C × 0.5 + D × 0.5
    可行性   = O × 0.4 + E × 0.4 + 资源匹配度 × 0.2
    总分     = 需求强度 × 0.5 + 可行性 × 0.5

逻辑解读：
  * 需求强度只看 C 和 D —— 趋势再热（C），没有活跃需求（D）也只是泡沫。
  * 资源匹配度占 0.2 且不可移除 —— 别人的好机会不等于你的好机会。
  * 总分对半开 —— 防止"趋势脑"压倒"务实脑"。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from oic.config import (
    BASELINE_WEIGHT,
    INTENT_PATTERNS,
    PATH_COEFF_BUZZ,
    PATH_COEFF_ELIGIBLE_GRADES,
    PATH_COEFF_INTENT,
    PATH_COEFF_PROVEN,
    PROVEN_PATTERNS,
    RESOURCE_COEFF,
    Weights,
)

# ---------------------------------------------------------------------------
# 三技能模型（v3 1.5）—— 直接编码进资源匹配度
# ---------------------------------------------------------------------------

SKILL_PATTERNS = {
    "product": re.compile(r"产品|设计|UX|体验"),
    "engineering": re.compile(r"工程|开发|技术|全栈|数据|AI|前端|后端|硬件"),
    "sales": re.compile(r"销售|运营|营销|商务|BD|增长|市场|达人"),
}

#: 资金档位分（PRIOR）
CAPITAL_TIERS: tuple[tuple[float, float], ...] = (
    (100_000, 60.0),
    (500_000, 70.0),
    (2_000_000, 80.0),
    (float("inf"), 90.0),
)


def capital_score(capital_rmb: float) -> float:
    """资金档位分。<10万→60｜10-50万→70｜50-200万→80｜>200万→90。"""
    if capital_rmb < 0:
        raise ValueError("资金不能为负")
    for ceiling, score in CAPITAL_TIERS:
        if capital_rmb < ceiling:
            return score
    return CAPITAL_TIERS[-1][1]


def skill_coverage(team_descriptions: Sequence[str]) -> float:
    """三技能覆盖度：产品/工程/销售 每覆盖一项 +33.3，封顶 100。

    团队缺哪个技能，资源匹配度掉 33 分，直接拖低可行性。
    """
    blob = " ".join(team_descriptions)
    # 按固定顺序遍历，绝不迭代 set —— 字符串哈希随机化会破坏可复现性。
    covered = sum(1 for key in ("product", "engineering", "sales")
                  if SKILL_PATTERNS[key].search(blob))
    return min(covered * 33.3, 100.0)


def resource_fit(capital_rmb: float, team_descriptions: Sequence[str]) -> float:
    """资源匹配度 = 资金档位分 × 0.5 + 团队技能覆盖度 × 0.5。"""
    return capital_score(capital_rmb) * 0.5 + skill_coverage(team_descriptions) * 0.5


# ---------------------------------------------------------------------------
# 变现系数（pathCoeff）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GradedText:
    """一段带来源等级的证据文本。

    ``grade`` 为 A（官方/财报）/ B（权威媒体）/ C（自媒体）。
    """

    text: str
    grade: str


@dataclass(frozen=True)
class PathCoeffResult:
    coefficient: float
    tier: str
    matched_terms: tuple[str, ...]
    rejected_c_grade_terms: tuple[str, ...]
    explanation: str


def path_coefficient(evidence: Iterable[GradedText]) -> PathCoeffResult:
    """三档变现系数，**C 级来源永不参与判定**。

    这是 v3 3.3 已识别漏洞的修复：原实现对全部证据文本做正则扫词，
    竞品自称"月销破万"就能骗到 1.2 系数。现在自媒体来源的成交词
    会被记录到 ``rejected_c_grade_terms`` 但不影响系数。
    """
    proven: list[str] = []
    intent: list[str] = []
    rejected: list[str] = []

    for item in evidence:
        eligible = item.grade in PATH_COEFF_ELIGIBLE_GRADES
        for term in PROVEN_PATTERNS:
            if term in item.text:
                (proven if eligible else rejected).append(term)
        if eligible:
            for term in INTENT_PATTERNS:
                if term in item.text:
                    intent.append(term)

    # 去重但保持确定性顺序：按首次出现的模式表顺序
    proven_u = tuple(t for t in PROVEN_PATTERNS if t in proven)
    intent_u = tuple(t for t in INTENT_PATTERNS if t in intent)
    rejected_u = tuple(t for t in PROVEN_PATTERNS if t in rejected)

    if proven_u:
        return PathCoeffResult(
            PATH_COEFF_PROVEN, "proven", proven_u, rejected_u,
            f"变现系数 {PATH_COEFF_PROVEN} —— A/B 级来源出现成交证据词: "
            + "、".join(proven_u),
        )
    if intent_u:
        return PathCoeffResult(
            PATH_COEFF_INTENT, "intent", intent_u, rejected_u,
            f"变现系数 {PATH_COEFF_INTENT} —— 有付费意愿信号: " + "、".join(intent_u),
        )
    note = ""
    if rejected_u:
        note = (f"（注意：C 级来源出现成交词 {'、'.join(rejected_u)}，"
                "按规则不予采信，疑似软文）")
    return PathCoeffResult(
        PATH_COEFF_BUZZ, "buzz", (), rejected_u,
        f"变现系数 {PATH_COEFF_BUZZ} —— 仅讨论热度，付费意愿未验证" + note,
    )


# ---------------------------------------------------------------------------
# 三级评分
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DimensionScores:
    demand_strength: float
    feasibility: float
    total: float
    explanation: tuple[str, ...]


def _coeff(base: float, weight: float) -> float:
    """公式系数 = 基准系数 × (当前权重 / 25)。"""
    return base * (weight / BASELINE_WEIGHT)


def score_dimensions(
    c: float, o: float, d: float, e: float,
    resource: float,
    weights: Weights,
) -> DimensionScores:
    """三级评分，每一步都返回可复算算式。"""
    for name, value in (("C", c), ("O", o), ("D", d), ("E", e), ("resource", resource)):
        if not 0.0 <= value <= 100.0:
            raise ValueError(f"{name} 必须在 0–100 之间，收到 {value}")

    c_coeff = _coeff(0.5, weights.c)
    d_coeff = _coeff(0.5, weights.d)
    o_coeff = _coeff(0.4, weights.o)
    e_coeff = _coeff(0.4, weights.e)

    demand = c * c_coeff + d * d_coeff
    feasibility = o * o_coeff + e * e_coeff + resource * RESOURCE_COEFF
    total = demand * 0.5 + feasibility * 0.5

    lines = (
        f"需求强度 = {c:g}×{c_coeff:g} + {d:g}×{d_coeff:g} = {demand:.2f}",
        f"可行性 = {o:g}×{o_coeff:g} + {e:g}×{e_coeff:g} + "
        f"{resource:g}×{RESOURCE_COEFF:g} = {feasibility:.2f}",
        f"总分 = {demand:.2f}×0.5 + {feasibility:.2f}×0.5 = {total:.2f}",
    )
    return DimensionScores(demand, feasibility, total, lines)


# ---------------------------------------------------------------------------
# 分级解读（v3 2.1）
# ---------------------------------------------------------------------------

_BANDS = {
    "C": ("多源共振，上升趋势明确", "有上升信号，但源数不足", "趋势信号偏弱"),
    "O": ("缺口清晰，现有方案差评率高", "存在缺口，但竞品已在填补", "缺口不显著，进入壁垒高"),
    "D": ("抱怨密度高，付费意愿已验证", "有需求信号，但付费路径待验证", "需求信号弱"),
    "E": ("TAM 超百亿，增速快", "TAM 中等，增速稳定", "TAM 偏小，利基市场"),
}


def interpret(dimension: str, score: float) -> str:
    """把 0–100 分翻译成分级解释。"""
    high, mid, low = _BANDS[dimension.upper()]
    if score >= 80:
        return high
    if score >= 65:
        return mid
    return low
