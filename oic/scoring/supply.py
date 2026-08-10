"""供给侧引擎 —— 系统的核心差异化（市面同类产品的共同盲区）。

第一性原理：商机本质 = 需求增速 > 供给增速 的交集。

    剪刀差 M = 需求增速% − 供给增速%
    死亡率 X = 近12月注销吊销数 / 存续企业数
    风险系数 = 1 − min(X × k, 0.5)

同时用同一批工商数据自动判定 Schwartz 市场成熟度 L1–L5，
从而自动给出文案策略方向 —— 这个连接是本项目原创。
"""

from __future__ import annotations

from dataclasses import dataclass

from oic.config import SupplyParams


@dataclass(frozen=True)
class SupplySignal:
    scissors_gap: float          # M，百分点
    death_rate: float            # X，0–1
    risk_coefficient: float      # 1 − min(X×k, 0.5)
    m_coefficient: float         # M 系数
    is_meatgrinder: bool         # 绞肉机红线
    sophistication: str          # L1–L5
    copy_strategy: str           # 对应文案策略
    recommended_action: str
    explanation: tuple[str, ...]


def scissors_gap(demand_growth_pct: float, supply_growth_pct: float) -> float:
    """剪刀差 M = 需求增速% − 供给增速%。"""
    return demand_growth_pct - supply_growth_pct


def death_rate(deregistered_12m: int, active_companies: int) -> float:
    """死亡率 X = 近12月注销吊销数 / 存续企业数。"""
    if active_companies <= 0:
        raise ValueError("存续企业数必须为正 —— 为 0 时死亡率无定义，应返回未知而非 1.0")
    if deregistered_12m < 0:
        raise ValueError("注销吊销数不能为负")
    return deregistered_12m / active_companies


def risk_coefficient(x: float, params: SupplyParams) -> float:
    """风险系数 = 1 − min(X × k, 0.5)。下限 0.5，避免单一指标把商机打死。"""
    return 1.0 - min(x * params.death_rate_k, 0.5)


def m_coefficient(m: float, x: float, params: SupplyParams) -> tuple[float, bool]:
    """M 系数分档 + 绞肉机判定。

    返回 ``(系数, 是否触发绞肉机红线)``。
    绞肉机 = 供给暴涨且大量企业在死 —— 需求跑了、供给还在涌入。
    """
    if m <= params.m_meatgrinder and x > params.high_death_rate:
        return 0.0, True
    if m > params.m_strong:
        return params.coeff_strong, False
    if m > params.m_open:
        return params.coeff_open, False
    if m >= params.m_balanced:
        return params.coeff_balanced, False
    return params.coeff_crowding, False


# --- Schwartz 成熟度 × 供给侧数据 ------------------------------------------

_SOPHISTICATION = {
    "L1": ("直接说这东西是什么", "最好做，直接上"),
    "L2": ("把效果说得更极致", "好做，抢速度"),
    "L3": ("讲独特机制（为什么你能做到）", "需真差异化"),
    "L4": ("讲更好的机制", "需技术壁垒"),
    "L5": ("只能靠身份认同", "不做，除非有社群"),
}


def sophistication_level(
    competitor_count: int,
    supply_growth_pct: float,
    x: float,
    params: SupplyParams,
) -> str:
    """从工商数据自动定级 L1–L5。

    Schwartz 判定成熟度的方法是"看此前有多少类似产品被宣传过" ——
    这正是供给侧数据能算的。

    注意：Schwartz 框架是营销经验总结，无同行评议，属判断辅助
    而非可测量指标；但"用供给侧数据自动定级"这个连接可被验证。
    """
    if competitor_count < 0:
        raise ValueError("同类企业数不能为负")
    # 饱和且注销率上升 —— 优先于纯数量判定
    if x > params.high_death_rate and supply_growth_pct <= 0:
        return "L5"
    if competitor_count < params.soph_l1_max:
        return "L1"
    if competitor_count < params.soph_l2_max:
        return "L2" if supply_growth_pct > 0 else "L3"
    if competitor_count < params.soph_l3_max:
        return "L3"
    return "L4" if supply_growth_pct > 0 else "L5"


def analyze_supply(
    demand_growth_pct: float,
    supply_growth_pct: float,
    deregistered_12m: int,
    active_companies: int,
    competitor_count: int,
    params: SupplyParams,
) -> SupplySignal:
    """跑完整条供给侧管线。"""
    m = scissors_gap(demand_growth_pct, supply_growth_pct)
    x = death_rate(deregistered_12m, active_companies)
    risk = risk_coefficient(x, params)
    coeff, meatgrinder = m_coefficient(m, x, params)
    level = sophistication_level(competitor_count, supply_growth_pct, x, params)
    copy_strategy, action = _SOPHISTICATION[level]

    lines = [
        f"剪刀差 M = {demand_growth_pct:g}% − {supply_growth_pct:g}% = {m:g}%",
        f"死亡率 X = {deregistered_12m} / {active_companies} = {x:.4f}",
        f"风险系数 = 1 − min({x:.4f}×{params.death_rate_k:g}, 0.5) = {risk:.4f}",
        f"M 系数 = {coeff:g}",
        f"成熟度 {level}（同类企业 {competitor_count} 家，供给增速 {supply_growth_pct:g}%）"
        f" → 文案策略：{copy_strategy}",
    ]
    if meatgrinder:
        lines.append(
            f"🔴 绞肉机红线触发：M={m:g}% ≤ {params.m_meatgrinder:g}% "
            f"且死亡率 {x:.2%} > {params.high_death_rate:.2%}"
        )
    if not params.calibrated:
        lines.append("⚠️ 供给侧参数(k / M分档 / 死亡率阈值)未经真实数据校准，为先验值")

    return SupplySignal(
        scissors_gap=m,
        death_rate=x,
        risk_coefficient=risk,
        m_coefficient=coeff,
        is_meatgrinder=meatgrinder,
        sophistication=level,
        copy_strategy=copy_strategy,
        recommended_action=action,
        explanation=tuple(lines),
    )
