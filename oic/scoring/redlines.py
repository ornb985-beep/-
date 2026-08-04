"""红线判定 —— 任一触发即排序分归零，不可被高分抵消。

五类红线：
  ① 合规类：监管、隐私、平台依赖、欺诈、现金断裂、重大声誉
  ② 市场结构类：M ≤ −30% 且死亡率高（绞肉机）
  ③ 切换势能 ≤ 0（用户不会换）
  ④ HHI > 1800 且 机会分 < 15（高度集中且无差异化空间）
  ⑤ 刷单风险分 > 60（数据不可信）

设计要点：红线是**代码仲裁**，不让 LLM 调和。
MAST 研究显示"输出冲突"是主要失败模式之一，解法是让确定性层裁决。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from oic.config import RedlineParams

COMPLIANCE_CATEGORIES = (
    "regulatory",       # 监管/牌照
    "privacy",          # 个人信息
    "platform_dependency",  # 平台依赖
    "fraud",            # 欺诈
    "cash_runway",      # 现金断裂
    "reputation",       # 重大声誉
    "intellectual_property",  # IP 侵权
)


@dataclass(frozen=True)
class Redline:
    code: str
    category: str
    message: str


@dataclass(frozen=True)
class RedlineVerdict:
    triggered: tuple[Redline, ...]
    passed: bool

    @property
    def multiplier(self) -> float:
        """归零因子 —— 用乘法而非分支，保证与排序公式一致。"""
        return 1.0 if self.passed else 0.0

    def explain(self) -> tuple[str, ...]:
        if self.passed:
            return ("红线检查：全部通过",)
        return tuple(
            f"🔴 红线[{r.code}/{r.category}] {r.message}" for r in self.triggered
        ) + ("排序分归零 —— 红线不可被高分抵消。",)


def evaluate_redlines(
    *,
    is_meatgrinder: bool,
    scissors_gap: float,
    death_rate: float,
    switching_potential: float,
    hhi: float,
    opportunity_score: float,
    fake_review_score: float,
    compliance_flags: Sequence[str] = (),
    params: RedlineParams,
) -> RedlineVerdict:
    """按固定顺序检查全部红线。

    ``compliance_flags`` 传入已确认的合规问题类别（见 COMPLIANCE_CATEGORIES）。
    """
    triggered: list[Redline] = []

    # ① 合规类 —— 按 COMPLIANCE_CATEGORIES 顺序遍历，保证确定性
    flags = set(compliance_flags)
    unknown = flags - set(COMPLIANCE_CATEGORIES)
    if unknown:
        raise ValueError(f"未知的合规类别: {sorted(unknown)}")
    for category in COMPLIANCE_CATEGORIES:
        if category in flags:
            triggered.append(Redline(
                "R1", category,
                f"已确认的合规问题（{category}）—— 落地前须经执业律师审查",
            ))

    # ② 市场结构类：绞肉机
    if is_meatgrinder:
        triggered.append(Redline(
            "R2", "market_structure",
            f"绞肉机：剪刀差 {scissors_gap:g}% 且死亡率 {death_rate:.2%} "
            "—— 需求在退、供给还在涌入",
        ))

    # ③ 切换势能
    if switching_potential <= 0:
        triggered.append(Redline(
            "R3", "switching",
            f"切换势能 {switching_potential:g} ≤ 0 —— 痛点可能真实，但用户不会换",
        ))

    # ④ 高度集中且无差异化空间
    if hhi > params.hhi_concentrated and opportunity_score < params.opportunity_floor:
        triggered.append(Redline(
            "R4", "concentration",
            f"HHI {hhi:.0f} > {params.hhi_concentrated:.0f} 且机会分 "
            f"{opportunity_score:g} < {params.opportunity_floor:g} "
            "—— 高度集中且无差异化空间",
        ))

    # ⑤ 数据不可信
    if fake_review_score > params.fake_review_max:
        triggered.append(Redline(
            "R5", "authenticity",
            f"刷单风险分 {fake_review_score:g} > {params.fake_review_max:g} "
            "—— 底层数据不可信，任何分析都是在错的数字上做的",
        ))

    return RedlineVerdict(tuple(triggered), not triggered)
