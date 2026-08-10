"""商业计划书生成 —— 把分析结果变成可执行的文档。

三条不可违背的规则：

  1. **每条论证必须引用可追溯证据**（品类 + 指标 + 来源 URL），
     不许出现"据估计""业内普遍认为"这类无主语断言。
  2. **结果写成条件区间 + 假设 + 反证条件**，不写点值。
  3. **导出前必须过证券边界闸与 AI 双标识闸**，与其他输出路径一致。

    python -m oic.deliver.business_plan --top 3
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from oic.compliance import ai_labeling as lbl
from oic.compliance import securities_guard as guard
from oic.config import DEFAULT_CONFIG, TRACKS, Config
from oic.deliver.plan_90day import Assumption, build_plan
from oic.deliver.resourcing import build_resource_plan
from oic.research.backtest import (
    DATA_DIR,
    CategorySignal,
    attach_outcomes,
    extract_signals,
    load_categories,
    load_outcomes,
)
from oic.research.dossier import Observation, load_observations

#: 未通过校准门槛时，BP 里必须原样出现的免责说明
UNCALIBRATED_BANNER = (
    "本计划书的所有数量结论均为**条件区间**，不是预测。\n"
    "系统的已解析真实结局仅 {n} 条（<30），未通过校准门槛（G2）。\n"
    "在此样本量下，n=6 时纯随机的 |ρ| 中位数即 0.293 —— 与实测值相同。\n"
    "**因此任何点值预测都是编造的，本文档拒绝提供。**\n"
    "请把下列区间当作「需要被证伪的假设」，而不是「可以指望的收入」。"
)


@dataclass(frozen=True)
class EvidenceRef:
    claim: str
    metric: str
    value: str
    source_url: str
    source_name: str

    def line(self) -> str:
        return (f"- {self.claim}\n"
                f"    - 依据：{self.metric} = {self.value}"
                f"（来源：{self.source_name} · {self.source_url}）")


@dataclass(frozen=True)
class BusinessPlan:
    rank: int
    category_key: str
    title: str
    track_key: str
    thesis: str
    evidence: tuple[EvidenceRef, ...]
    risks: tuple[str, ...]
    plan_markdown: str
    resource_markdown: str
    calibration_n: int

    def render(self) -> str:
        track = TRACKS[self.track_key]
        lines = [
            f"# 商业计划书 #{self.rank} · {self.title}",
            "",
            "> " + UNCALIBRATED_BANNER.format(n=self.calibration_n).replace("\n", "\n> "),
            "",
            "## 一、机会论证",
            "",
            self.thesis,
            "",
            "### 支撑证据（全部可追溯）",
            "",
        ]
        lines.extend(e.line() for e in self.evidence)
        lines.extend([
            "",
            "## 二、风险与反对意见",
            "",
        ])
        lines.extend(f"- {r}" for r in self.risks)
        lines.extend([
            "",
            f"## 三、赛道与成功口径",
            "",
            f"- 赛道：**{track.name}**",
            f"- 成功定义：{track.outcome_label}",
            f"- 结局可解析周期：{track.resolution_days} 天",
            f"- 早期代理信号：{track.surrogate_label}"
            f"（{track.surrogate_days} 天）—— **只用于排序，不用于宣称成功**",
            "",
            self.plan_markdown,
            "",
            self.resource_markdown,
        ])
        return "\n".join(lines)


def _evidence_for(category_key: str, observations: Sequence[Observation]
                  ) -> tuple[EvidenceRef, ...]:
    """把该品类的观测转成可引用的证据条目。"""
    refs: list[EvidenceRef] = []
    for obs in observations:
        if obs.category_key != category_key:
            continue
        refs.append(EvidenceRef(
            claim=obs.snippet.strip()[:80],
            metric=obs.metric_key.label(),
            value=f"{obs.value:,.4g}{obs.unit_note and ' · ' + obs.unit_note or ''}",
            source_url=obs.source_url,
            source_name=obs.source_name,
        ))
    return tuple(refs)


def _rank_candidates(signals: Sequence[CategorySignal]) -> tuple[CategorySignal, ...]:
    """挑候选。

    **刻意不按需求增速排序** —— 回测已证明它在本样本上无信号
    （p=0.70，与纯随机中位数相同）。改用可审计的启发式：
    数据完整度优先，其次是双标签均为正。

    这不是"更好的排序"，这是"在没有验证过的排序面前保持诚实"。
    """
    def key(signal: CategorySignal) -> tuple:
        both_positive = (signal.outcome_demand == 1
                         and signal.outcome_opportunity == 1)
        completeness = sum([
            signal.demand_growth is not None,
            signal.supply_growth is not None,
            signal.outcome_demand is not None,
        ])
        return (-int(both_positive), -completeness, signal.key)

    return tuple(sorted(signals, key=key))


def build_business_plans(
    top: int = 3, config: Config = DEFAULT_CONFIG
) -> tuple[BusinessPlan, ...]:
    categories = load_categories(DATA_DIR / "categories.jsonl")
    observations = load_observations(DATA_DIR / "observations.jsonl")
    signals = extract_signals(categories, observations)
    attach_outcomes(signals, load_outcomes(DATA_DIR / "outcomes.jsonl"))

    resolved = sum(1 for s in signals if s.outcome_demand is not None)
    ranked = _rank_candidates(signals)[:top]

    track = config.track
    plans: list[BusinessPlan] = []

    for i, signal in enumerate(ranked, start=1):
        assumptions = (
            Assumption(
                "假设A", f"{track.surrogate_label}",
                f"第 {track.surrogate_days} 天留资/候补低于门槛的一半 → 痛点不成立，立即止损",
                track.surrogate_days,
            ),
            Assumption(
                "假设B", "单位获客成本 ≤ 80 元",
                "首轮投放 CAC > 160 元且无下降趋势 → 渠道不成立，换渠道或停",
                21,
            ),
            Assumption(
                "假设C", "退货率 < 15%（或 SaaS：首周留存 > 40%）",
                "超过阈值 → 产品与预期不符，回到选品/需求验证",
                45,
            ),
        )

        outcome = (
            f"若假设 A、B、C 同时成立，则第 90 天达成「{track.outcome_label}」"
            f"的**先验概率区间**为 {track.base_rate_prior:.0%} 上下的宽区间。\n\n"
            "**注意**：这个先验来自赛道基础率，不是对本商机的预测。"
            "系统当前无法给出商机层面的概率——已解析结局不足，"
            "`oic/scoring/kelly.py` 与概率映射层都会拒绝输出。\n\n"
            "**三条假设中任意一条被证伪，上述区间即作废，不要继续按它决策。**"
        )

        plan = build_plan(
            opportunity_title=signal.name,
            track=track,
            total_budget_rmb=200_000.0,
            assumptions=assumptions,
            outcome_statement=outcome,
            calibration_note=(
                f"校准状态：已解析真实结局 {resolved} 条 < 30，校准未建立。"
                "本文档不提供点值预测。"
            ),
        )

        resources = build_resource_plan(
            capital_rmb=500_000.0,
            team_descriptions=("产品设计", "全栈开发"),
            track_key=track.key,
            stage_budgets=tuple((s.name, s.budget_cap_rmb) for s in plan.stages),
        )

        thesis = (
            f"「{signal.name}」进入候选的理由是**数据完整度**与**双标签表现**，"
            f"不是分数高。\n\n"
            f"as-of 2022 需求增速 "
            f"{'%.1f%%' % signal.demand_growth if signal.demand_growth is not None else '未知'}，"
            f"供给增速 "
            f"{'%.1f%%' % signal.supply_growth if signal.supply_growth is not None else '**未知**'}，"
            f"剪刀差 "
            f"{'%.1f%%' % signal.scissors if signal.scissors is not None else '**无法计算**'}。"
        )

        risks: list[str] = []
        if signal.supply_growth is None:
            risks.append(
                "**供给侧数据缺失** —— 剪刀差算不出来，无法判断窗口是开是关。"
                "这是本系统最大差异化的失效，应优先补齐（招股书管线可解）"
            )
        if signal.outcome_opportunity == 0 and signal.outcome_demand == 1:
            risks.append(
                f"**该品类历史上出现过「增长但不赚钱」** —— {signal.outcome_note}"
            )
        risks.append(
            "样本池只有 17 个品类、8 条已解析结局，且多为消费品类、"
            "同受宏观影响，有效样本量比数字更小"
        )
        risks.append(
            "本分析的来源多为行业报告（B/C 级），存在 85% 量级的跨源冲突；"
            "招股书（A 级）管线已建好但本环境无法取数"
        )

        plans.append(BusinessPlan(
            rank=i, category_key=signal.key, title=signal.name,
            track_key=track.key, thesis=thesis,
            evidence=_evidence_for(signal.key, observations),
            risks=tuple(risks),
            plan_markdown=plan.render(),
            resource_markdown=resources.render(),
            calibration_n=resolved,
        ))

    return tuple(plans)


def main(argv: list[str]) -> int:
    top = 3
    if "--top" in argv:
        idx = argv.index("--top")
        if idx + 1 < len(argv):
            top = int(argv[idx + 1])

    plans = build_business_plans(top)
    provider = lbl.ProviderIdentity(name="OIC", code="ALG-PENDING-0001")

    out_dir = Path(__file__).resolve().parents[2] / "data" / "deliverables"
    write = "--write" in argv
    if write:
        out_dir.mkdir(parents=True, exist_ok=True)

    for plan in plans:
        body = plan.render()
        # 与所有输出路径一致：证券边界闸 → AI 双标识闸
        body = guard.assert_safe(body)
        content = lbl.label(body, provider, "2026-08-04T00:00:00Z")
        lbl.assert_labeled(content)

        if write:
            path = out_dir / f"BP-{plan.rank}-{plan.category_key}.md"
            path.write_text(content.body, encoding="utf-8")
            print(f"已写入 {path}")
        else:
            print(content.body)
            print("\n" + "=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
