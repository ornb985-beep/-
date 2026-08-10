"""资源规划 —— 需要什么人、多少钱、在哪些平台做什么。

技能缺口直接复用 ``scoring/dimensions.py::skill_coverage`` 的三技能模型
（产品/工程/销售），不另造一套口径。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from oic.scoring.dimensions import SKILL_PATTERNS, capital_score, skill_coverage

#: 三技能在不同赛道的优先级 —— 缺哪个最致命
TRACK_SKILL_PRIORITY: dict[str, tuple[str, ...]] = {
    "consumer_goods": ("sales", "product", "engineering"),
    "ai_saas": ("engineering", "product", "sales"),
}

SKILL_LABEL = {
    "product": "产品/设计",
    "engineering": "工程/技术",
    "sales": "销售/运营/增长",
}

#: 各技能的补位方式与月成本区间（元，PRIOR —— 需按地区与时点校准）
HIRING_OPTIONS: dict[str, tuple[str, int, int]] = {
    "product": ("兼职产品顾问 或 创始人自补（前期可行）", 8_000, 25_000),
    "engineering": ("外包 MVP 或 技术合伙人", 15_000, 45_000),
    "sales": ("达人分销/代运营（按效果付费优于固定工资）", 6_000, 30_000),
}


@dataclass(frozen=True)
class SkillGap:
    skill: str
    covered: bool
    priority_rank: int
    remedy: str
    monthly_cost_low: int
    monthly_cost_high: int

    def line(self) -> str:
        if self.covered:
            return f"- ✅ {SKILL_LABEL[self.skill]}：已覆盖"
        return (f"- ❌ **{SKILL_LABEL[self.skill]}**（该赛道第 {self.priority_rank} 优先）"
                f"：{self.remedy}，约 {self.monthly_cost_low:,}–"
                f"{self.monthly_cost_high:,} 元/月")


@dataclass(frozen=True)
class ResourcePlan:
    capital_rmb: float
    capital_tier_score: float
    skill_coverage_pct: float
    gaps: tuple[SkillGap, ...]
    budget_by_stage: tuple[tuple[str, float], ...]
    platforms: tuple[tuple[str, str], ...]
    warnings: tuple[str, ...]

    def render(self) -> str:
        lines = [
            "## 资源规划",
            "",
            f"**资金**：{self.capital_rmb:,.0f} 元（档位分 {self.capital_tier_score:g}）",
            f"**技能覆盖度**：{self.skill_coverage_pct:.1f}/100",
            "",
            "### 团队缺口",
            "",
        ]
        lines.extend(g.line() for g in self.gaps)
        lines.extend(["", "### 分阶段预算上限", ""])
        lines.extend(f"- {name}：{amount:,.0f} 元" for name, amount in self.budget_by_stage)
        lines.extend(["", "### 平台与动作", ""])
        lines.extend(f"- **{platform}**：{action}" for platform, action in self.platforms)
        if self.warnings:
            lines.extend(["", "### ⚠️ 风险提示", ""])
            lines.extend(f"- {w}" for w in self.warnings)
        return "\n".join(lines)


#: 各赛道的平台动作清单
TRACK_PLATFORMS: dict[str, tuple[tuple[str, str], ...]] = {
    "consumer_goods": (
        ("1688 / 阿里巴巴", "供应商询价、打样、比对起订量"),
        ("抖音", "短视频测流量 → 小店挂链 → 达人分销"),
        ("小红书", "种草笔记测卖点，评论区收集反对意见"),
        ("拼多多 / 天猫", "第二平台，分散平台依赖风险"),
        ("私域（企微/社群）", "复购与口碑，降低对平台流量的依赖"),
    ),
    "ai_saas": (
        ("落地页 + 候补名单", "先卖后做，验证付费意愿"),
        ("V2EX / 即刻 / Reddit", "垂直社区冷启动，重点收集反对意见"),
        ("微信公众号 / 小红书", "内容获客，测算 CAC"),
        ("Product Hunt", "海外曝光（若面向海外）"),
    ),
}


def build_resource_plan(
    capital_rmb: float,
    team_descriptions: Sequence[str],
    track_key: str,
    stage_budgets: Sequence[tuple[str, float]],
) -> ResourcePlan:
    """生成资源规划。技能判定复用评分层的同一套正则，口径不分裂。"""
    if capital_rmb < 0:
        raise ValueError("资金不能为负")

    blob = " ".join(team_descriptions)
    priority = TRACK_SKILL_PRIORITY.get(track_key, ("product", "engineering", "sales"))

    gaps: list[SkillGap] = []
    for rank, skill in enumerate(priority, start=1):
        covered = bool(SKILL_PATTERNS[skill].search(blob))
        remedy, low, high = HIRING_OPTIONS[skill]
        gaps.append(SkillGap(skill, covered, rank, remedy, low, high))

    warnings: list[str] = []
    missing_top = [g for g in gaps if not g.covered and g.priority_rank == 1]
    if missing_top:
        warnings.append(
            f"缺该赛道第一优先技能（{SKILL_LABEL[missing_top[0].skill]}）——"
            "这是资源匹配度里权重最高的一项，建议先补齐再启动，"
            "或把它作为首个阶段的验证目标"
        )

    total_budget = sum(amount for _, amount in stage_budgets)
    if total_budget > capital_rmb:
        warnings.append(
            f"分阶段预算合计 {total_budget:,.0f} 元 超过可用资金 "
            f"{capital_rmb:,.0f} 元 —— 必须先缩减范围"
        )
    elif total_budget > capital_rmb * 0.5:
        warnings.append(
            f"本项目将占用 {total_budget / capital_rmb:.0%} 的可用资金 ——"
            "单一商机占比过高，与「反复下小注」相悖"
        )

    return ResourcePlan(
        capital_rmb=capital_rmb,
        capital_tier_score=capital_score(capital_rmb),
        skill_coverage_pct=skill_coverage(team_descriptions),
        gaps=tuple(gaps),
        budget_by_stage=tuple(stage_budgets),
        platforms=TRACK_PLATFORMS.get(track_key, ()),
        warnings=tuple(warnings),
    )
