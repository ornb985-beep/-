"""90 天落地执行 —— 四阶段，每阶段带量化止损门槛。

设计原则：**每个阶段必须能被证伪。**

一个没有止损线的计划不是计划，是许愿。所以每阶段都必须回答：
什么观测出现就说明这条路走不通、应当立刻停？
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from oic.config import TrackProfile


@dataclass(frozen=True)
class Assumption:
    """一条可证伪的假设。"""

    key: str
    statement: str
    falsified_when: str          # 什么观测出现即证伪
    check_by_day: int

    def line(self) -> str:
        return (f"**{self.key}**：{self.statement}\n"
                f"    - 证伪条件（第 {self.check_by_day} 天检查）：{self.falsified_when}")


@dataclass(frozen=True)
class Stage:
    index: int
    name: str
    day_start: int
    day_end: int
    objective: str
    actions: tuple[str, ...]
    gate_metric: str
    gate_pass: str
    stop_loss: str
    budget_cap_rmb: float

    def lines(self) -> tuple[str, ...]:
        out = [
            f"### 阶段 {self.index}（第 {self.day_start}–{self.day_end} 天）· {self.name}",
            "",
            f"**目标**：{self.objective}",
            "",
            "**动作**：",
        ]
        out.extend(f"- {a}" for a in self.actions)
        out.extend([
            "",
            f"**通过门槛**：{self.gate_metric} {self.gate_pass}",
            f"**止损线**：{self.stop_loss}",
            f"**本阶段预算上限**：{self.budget_cap_rmb:,.0f} 元"
            f"（超支即停，不得挪用下阶段预算）",
            "",
        ])
        return tuple(out)


@dataclass(frozen=True)
class NinetyDayPlan:
    opportunity_title: str
    track: str
    stages: tuple[Stage, ...]
    assumptions: tuple[Assumption, ...]
    total_budget_rmb: float
    outcome_statement: str
    calibration_note: str

    def render(self) -> str:
        lines = [
            f"## 90 天落地执行 · {self.opportunity_title}",
            "",
            f"赛道：{self.track}　总预算上限：{self.total_budget_rmb:,.0f} 元",
            "",
            "### 关键假设（全部可证伪）",
            "",
        ]
        lines.extend(a.line() for a in self.assumptions)
        lines.extend(["", "---", ""])
        for stage in self.stages:
            lines.extend(stage.lines())
        lines.extend([
            "---",
            "",
            "### 预期结果",
            "",
            self.outcome_statement,
            "",
            f"> {self.calibration_note}",
        ])
        return "\n".join(lines)


#: 各阶段预算占比（PRIOR）—— 前期小注试探，验证通过才加仓
STAGE_BUDGET_SHARE = (0.10, 0.20, 0.30, 0.40)


def build_plan(
    opportunity_title: str,
    track: TrackProfile,
    total_budget_rmb: float,
    assumptions: Sequence[Assumption],
    outcome_statement: str,
    calibration_note: str,
) -> NinetyDayPlan:
    """按赛道的 stage_gates 生成四阶段计划。

    阶段定义来自 ``config.TrackProfile.stage_gates``，
    换赛道不改这里的代码。
    """
    if total_budget_rmb <= 0:
        raise ValueError("预算必须为正")
    if not track.stage_gates:
        raise ValueError(f"赛道 {track.key} 未定义 stage_gates")
    if len(track.stage_gates) != len(STAGE_BUDGET_SHARE):
        raise ValueError(
            f"赛道 {track.key} 有 {len(track.stage_gates)} 个阶段，"
            f"但预算占比表定义了 {len(STAGE_BUDGET_SHARE)} 档"
        )

    stages: list[Stage] = []
    day_start = 1
    for i, (name, day_end, gate) in enumerate(track.stage_gates):
        share = STAGE_BUDGET_SHARE[i]
        stages.append(Stage(
            index=i + 1,
            name=name,
            day_start=day_start,
            day_end=day_end,
            objective=gate,
            actions=_actions_for(track.key, i),
            gate_metric=gate,
            gate_pass="达标则进入下一阶段",
            stop_loss=f"未达「{gate}」即降级为观察，停止追加投入",
            budget_cap_rmb=total_budget_rmb * share,
        ))
        day_start = day_end + 1

    return NinetyDayPlan(
        opportunity_title=opportunity_title,
        track=track.name,
        stages=tuple(stages),
        assumptions=tuple(assumptions),
        total_budget_rmb=total_budget_rmb,
        outcome_statement=outcome_statement,
        calibration_note=calibration_note,
    )


#: 各赛道各阶段的具体动作（含平台）
_ACTIONS: dict[str, tuple[tuple[str, ...], ...]] = {
    "consumer_goods": (
        ("1688/阿里巴巴：询价 5–10 家供应商，比对起订量与打样费",
         "抖音/小红书：发 3 条测试短视频，同一卖点不同钩子",
         "记录每条的完播率与评论区反对意见（反对意见比点赞更有信息量）"),
        ("小批量下单，抖音小店/小红书店铺挂链接",
         "投放测试：单条预算不超过阶段预算的 1/5",
         "记录转化率、退货率、客服问题 TOP3"),
        ("锁定表现最好的 1–2 个 SKU，砍掉其余",
         "达人合作：优先腰部达人（性价比高于头部）",
         "供应链谈判：以实际销量换成本下降"),
        ("建立复购机制（私域/会员）",
         "拓展第二平台（拼多多/天猫）分散平台依赖风险",
         "复盘：哪些假设被证伪，哪些被验证"),
    ),
    "ai_saas": (
        ("只做一个功能的 MVP，不做后台不做登录",
         "落地页 + 候补名单，明确写清价格",
         "在垂直社区（V2EX/即刻/Reddit 相关版块）发布并收集反对意见"),
        ("邀请 50 个种子用户，逐个访谈（Moesta：10 个精选访谈即可覆盖主要模式）",
         "记录周活与实际使用路径，不看自我报告",
         "NPS 调研"),
        ("上线付费，先做年付折扣验证支付意愿",
         "监控激活率与首周留存",
         "根据流失访谈迭代"),
        ("拓展获客渠道，测算 CAC 与回本周期",
         "复盘：单位经济模型是否成立"),
    ),
}


def _actions_for(track_key: str, stage_index: int) -> tuple[str, ...]:
    stages = _ACTIONS.get(track_key)
    if not stages or stage_index >= len(stages):
        return ("（该赛道的阶段动作未定义，需人工补充）",)
    return stages[stage_index]
