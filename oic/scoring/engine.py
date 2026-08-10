"""评分引擎 —— 把全部维度合成排序分，并提供可复现性硬断言。

    排序分 = 总分 × 变现系数 × M系数 × 风险系数 × 真实性系数
            且 切换势能 > 0 且 无红线触发

``verify_scores`` 是整个架构正确性的自动检测器：它双跑同一输入并断言
结果**逐字节相同**。只有当所有公式都跑在本地代码里（铁律 1）时才可能通过。
把任何 LLM 调用、时钟读取、随机数或 set 迭代混进计算层，它都会失败。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Sequence

from oic.config import Config, DEFAULT_CONFIG
from oic.scoring import concentration as conc
from oic.scoring import differentiation as diff
from oic.scoring import dimensions as dim
from oic.scoring import redlines as rl
from oic.scoring import supply as sup
from oic.scoring import switching as sw

#: 真实性系数：1 − min(刷单风险分/100 × 系数, 0.5)。PRIOR。
AUTHENTICITY_K = 1.0


@dataclass(frozen=True)
class OpportunityInput:
    """商机的完整输入。

    C/O/D/E 四维分由 LLM 给出（它只当评分员），其余全部来自
    确定性采集与计算 —— 这条分界线就是铁律 1。
    """

    opportunity_id: str
    title: str

    # --- LLM 打分的四维（0–100）---
    c: float
    o: float
    d: float
    e: float

    # --- 资源（用户自述）---
    capital_rmb: float
    team_descriptions: tuple[str, ...]

    # --- 供给侧（企查查 / 榜单 API）---
    demand_growth_pct: float
    supply_growth_pct: float
    deregistered_12m: int
    active_companies: int
    competitor_count: int

    # --- 切换势能四力（0–100）---
    push: float
    pull: float
    anxiety: float
    inertia: float

    # --- 差异化（Ulwick 1–10 量表）---
    importance: float
    satisfaction: float

    # --- 竞争格局（份额百分数）---
    market_shares_pct: tuple[float, ...]

    # --- 证据（带来源等级）---
    evidence: tuple[dim.GradedText, ...] = ()

    # --- 风险 ---
    fake_review_score: float = 0.0
    compliance_flags: tuple[str, ...] = ()

    category: str = "unknown"


@dataclass(frozen=True)
class ScoreResult:
    opportunity_id: str
    engine_version: int

    demand_strength: float
    feasibility: float
    total: float

    path_coefficient: float
    m_coefficient: float
    risk_coefficient: float
    authenticity_coefficient: float

    rank_score: float
    switching_potential: float
    opportunity_score: float
    hhi: float
    sophistication: str

    redlines: tuple[str, ...]
    passed_redlines: bool

    audit: tuple[str, ...] = field(default_factory=tuple)

    def to_canonical_json(self) -> str:
        """确定性序列化 —— 用于可复现性比对与审计留痕。"""
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"))


def authenticity_coefficient(fake_review_score: float, k: float = AUTHENTICITY_K) -> float:
    """真实性系数 = 1 − min(刷单风险分/100 × k, 0.5)。

    第三方拿不到平台级反作弊信号（设备指纹、关系网络），
    所以这只是"真实性置信度"，不是确定结论 —— 因此下限设在 0.5，
    不允许单一代理指标把商机直接打死（那是 R5 红线的职责）。
    """
    if not 0.0 <= fake_review_score <= 100.0:
        raise ValueError("刷单风险分必须在 0–100 之间")
    return 1.0 - min(fake_review_score / 100.0 * k, 0.5)


def compute_all_scores(
    opportunity: OpportunityInput, config: Config = DEFAULT_CONFIG
) -> ScoreResult:
    """跑完整条确定性计算管线。

    此函数内**不得**出现：网络调用、模型调用、``time``、``random``、
    未排序的 set/dict 迭代。任何一条都会让 ``verify_scores`` 失败。
    """
    audit: list[str] = []

    # --- 资源匹配度 ---
    resource = dim.resource_fit(opportunity.capital_rmb, opportunity.team_descriptions)
    audit.append(
        f"资源匹配度 = 资金档位{dim.capital_score(opportunity.capital_rmb):g}×0.5 + "
        f"技能覆盖{dim.skill_coverage(opportunity.team_descriptions):g}×0.5 = {resource:.2f}"
    )

    # --- 三级评分 ---
    scores = dim.score_dimensions(
        opportunity.c, opportunity.o, opportunity.d, opportunity.e,
        resource, config.weights,
    )
    audit.extend(scores.explanation)

    # --- 变现系数 ---
    path = dim.path_coefficient(opportunity.evidence)
    audit.append(path.explanation)

    # --- 供给侧 ---
    supply = sup.analyze_supply(
        opportunity.demand_growth_pct, opportunity.supply_growth_pct,
        opportunity.deregistered_12m, opportunity.active_companies,
        opportunity.competitor_count, config.supply,
    )
    audit.extend(supply.explanation)

    # --- 切换势能 ---
    switching = sw.switching_potential(
        opportunity.push, opportunity.pull, opportunity.anxiety, opportunity.inertia
    )
    audit.extend(switching.explanation)

    # --- 差异化 ---
    opp_score = diff.opportunity_score(opportunity.importance, opportunity.satisfaction)
    audit.append(opp_score.explanation)

    # --- 竞争格局 ---
    market = conc.analyze_concentration(opportunity.market_shares_pct)
    audit.extend(market.explanation)

    # --- 真实性 ---
    authenticity = authenticity_coefficient(opportunity.fake_review_score)
    audit.append(
        f"真实性系数 = 1 − min({opportunity.fake_review_score:g}/100, 0.5) = {authenticity:.4f}"
    )

    # --- 红线 ---
    verdict = rl.evaluate_redlines(
        is_meatgrinder=supply.is_meatgrinder,
        scissors_gap=supply.scissors_gap,
        death_rate=supply.death_rate,
        switching_potential=switching.potential,
        hhi=market.hhi,
        opportunity_score=opp_score.value,
        fake_review_score=opportunity.fake_review_score,
        compliance_flags=opportunity.compliance_flags,
        params=config.redlines,
    )
    audit.extend(verdict.explain())

    # --- 排序分 ---
    rank = (
        scores.total
        * path.coefficient
        * supply.m_coefficient
        * supply.risk_coefficient
        * authenticity
        * verdict.multiplier
    )
    audit.append(
        f"排序分 = {scores.total:.2f} × {path.coefficient:g} × {supply.m_coefficient:g}"
        f" × {supply.risk_coefficient:.4f} × {authenticity:.4f}"
        f" × {verdict.multiplier:g}(红线) = {rank:.4f}"
    )

    notice = config.uncalibrated_notice()
    if notice:
        audit.append("⚠️ " + notice)

    from oic import SCORING_ENGINE_VERSION

    return ScoreResult(
        opportunity_id=opportunity.opportunity_id,
        engine_version=SCORING_ENGINE_VERSION,
        demand_strength=scores.demand_strength,
        feasibility=scores.feasibility,
        total=scores.total,
        path_coefficient=path.coefficient,
        m_coefficient=supply.m_coefficient,
        risk_coefficient=supply.risk_coefficient,
        authenticity_coefficient=authenticity,
        rank_score=rank,
        switching_potential=switching.potential,
        opportunity_score=opp_score.value,
        hhi=market.hhi,
        sophistication=supply.sophistication,
        redlines=tuple(r.code for r in verdict.triggered),
        passed_redlines=verdict.passed,
        audit=tuple(audit),
    )


class ReproducibilityError(AssertionError):
    """评分不可复现 —— 说明有非确定性成分混进了计算层。"""


def verify_scores(
    opportunity: OpportunityInput, config: Config = DEFAULT_CONFIG
) -> ScoreResult:
    """双跑并断言完全一致（G0 门）。

    这个断言只有在"公式跑在代码里"时才能通过 ——
    它是架构正确性的自动检测器，不是普通的单元测试。
    """
    first = compute_all_scores(opportunity, config)
    second = compute_all_scores(opportunity, config)
    if first.to_canonical_json() != second.to_canonical_json():
        raise ReproducibilityError(
            "评分不可复现 —— 检查计算层是否混入了 LLM 调用、时钟、随机数或未排序的 set 迭代。\n"
            f"第一次: {first.to_canonical_json()}\n"
            f"第二次: {second.to_canonical_json()}"
        )
    return first


def rank_opportunities(
    opportunities: Sequence[OpportunityInput], config: Config = DEFAULT_CONFIG
) -> tuple[ScoreResult, ...]:
    """批量评分并排序。

    并列时用 opportunity_id 作次级键 —— 保证排序本身也是确定性的
    （Python 的 sorted 稳定，但输入顺序变化会改变并列项次序）。
    """
    results = [compute_all_scores(o, config) for o in opportunities]
    return tuple(sorted(results, key=lambda r: (-r.rank_score, r.opportunity_id)))
