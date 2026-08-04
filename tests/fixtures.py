"""测试用的商机样本。"""

from __future__ import annotations

from oic.scoring.dimensions import GradedText
from oic.scoring.engine import OpportunityInput


def healthy_opportunity(**overrides) -> OpportunityInput:
    """一个各项都健康的商机 —— 用作基线。"""
    defaults = dict(
        opportunity_id="OPP-HEALTHY",
        title="露营便携咖啡器具",
        c=82.0, o=70.0, d=88.0, e=75.0,
        capital_rmb=300_000.0,
        team_descriptions=("全栈开发", "增长运营", "工业设计"),
        demand_growth_pct=45.0,
        supply_growth_pct=12.0,
        deregistered_12m=40,
        active_companies=800,
        competitor_count=35,
        push=72.0, pull=68.0, anxiety=30.0, inertia=25.0,
        importance=9.0, satisfaction=4.0,
        market_shares_pct=(18.0, 12.0, 9.0, 7.0, 5.0, 4.0, 3.0),
        evidence=(
            GradedText("该类目月销破万单", "A"),
            GradedText("客单价接受度高", "B"),
        ),
        fake_review_score=15.0,
        compliance_flags=(),
        category="户外露营",
    )
    defaults.update(overrides)
    return OpportunityInput(**defaults)


def meatgrinder_opportunity() -> OpportunityInput:
    """绞肉机：供给暴涨且大量企业在死。"""
    return healthy_opportunity(
        opportunity_id="OPP-MEATGRINDER",
        demand_growth_pct=-20.0,
        supply_growth_pct=25.0,
        deregistered_12m=300,
        active_companies=1000,
    )


def no_switch_opportunity() -> OpportunityInput:
    """痛点真实、市场够大，但用户就是不换。"""
    return healthy_opportunity(
        opportunity_id="OPP-NOSWITCH",
        push=30.0, pull=25.0, anxiety=60.0, inertia=55.0,
    )
