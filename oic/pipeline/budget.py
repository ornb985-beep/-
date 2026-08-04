"""每日成本硬顶 —— 超限抛错，不静默降级。

## 为什么是抛错而不是降级

静默降级会让系统在配额耗尽后继续"工作"，但产出质量断崖下跌，
而调用方毫不知情。等你发现时，已经基于半截数据做了几周决策。

所以本模块的行为是：**配额耗尽 → 抛 BudgetExhausted → 上层如实上报
"今天只处理了 N 条"**。这与「不足不编造」是同一条纪律。

## 配额自洽性检查

设计文档里如果一边写"LLM ≤12 次/天"、另一边的漏斗写"每天约 1000 次调用"，
这两个数不可能同真。``assert_funnel_feasible()`` 会在启动时就把这类
自相矛盾拦下来，而不是等到线上第 13 次调用才失败。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence


class Resource:
    SEARCH = "search"
    FETCH = "fetch"
    LLM = "llm"


ALL_RESOURCES = (Resource.SEARCH, Resource.FETCH, Resource.LLM)


class BudgetExhausted(RuntimeError):
    """配额耗尽。调用方必须如实上报处理量，不得凑数。"""


class BudgetMisconfigured(ValueError):
    """配额设置自相矛盾 —— 启动即失败，好过线上才发现。"""


@dataclass(frozen=True)
class DailyCaps:
    """每日硬顶。默认值取自设计文档的保守一档。"""

    search: int = 10
    fetch: int = 30
    llm: int = 12

    def get(self, resource: str) -> int:
        if resource not in ALL_RESOURCES:
            raise ValueError(f"未知资源类型: {resource}")
        return {Resource.SEARCH: self.search,
                Resource.FETCH: self.fetch,
                Resource.LLM: self.llm}[resource]


@dataclass(frozen=True)
class Spend:
    """一笔支出。``reason`` 必填 —— 花不出理由的钱不该花。"""

    resource: str
    amount: int
    reason: str


class Ledger:
    """配额账本。每一笔都记原因，可审计。"""

    def __init__(self, caps: DailyCaps, day: str) -> None:
        self._caps = caps
        self._day = day
        self._spent: dict[str, int] = {r: 0 for r in ALL_RESOURCES}
        self._entries: list[Spend] = []

    @property
    def day(self) -> str:
        return self._day

    @property
    def caps(self) -> DailyCaps:
        return self._caps

    def spent(self, resource: str) -> int:
        return self._spent[resource]

    def remaining(self, resource: str) -> int:
        return max(self._caps.get(resource) - self._spent[resource], 0)

    def utilization(self, resource: str) -> float:
        cap = self._caps.get(resource)
        return self._spent[resource] / cap if cap else 1.0

    def can_afford(self, resource: str, amount: int = 1) -> bool:
        return self.remaining(resource) >= amount

    def consume(self, resource: str, amount: int = 1, reason: str = "") -> None:
        """扣配额。不够就抛错 —— **不部分扣减，不静默跳过**。"""
        if resource not in ALL_RESOURCES:
            raise ValueError(f"未知资源类型: {resource}")
        if amount <= 0:
            raise ValueError("消耗量必须为正")
        if not reason.strip():
            raise ValueError("必须写明用途 —— 花不出理由的配额不该花")

        if not self.can_afford(resource, amount):
            raise BudgetExhausted(
                f"{self._day} 的 {resource} 配额已耗尽："
                f"已用 {self._spent[resource]}/{self._caps.get(resource)}，"
                f"本次还需 {amount}。\n"
                "请如实上报「今天只处理了 N 条」，不要降级凑数。"
            )
        self._spent[resource] += amount
        self._entries.append(Spend(resource, amount, reason.strip()))

    def entries(self) -> tuple[Spend, ...]:
        return tuple(self._entries)

    def report(self) -> tuple[str, ...]:
        lines = [f"配额账本 · {self._day}"]
        for resource in ALL_RESOURCES:
            cap = self._caps.get(resource)
            used = self._spent[resource]
            flag = "  ⚠️ 已耗尽" if used >= cap else ""
            lines.append(f"  {resource:<7} {used:>4}/{cap:<4}"
                         f"（{self.utilization(resource):.0%}）{flag}")
        return tuple(lines)


# ---------------------------------------------------------------------------
# 漏斗自洽性
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FunnelStage:
    name: str
    items_in: int
    items_out: int
    resource: str | None = None       # None = 零成本（纯程序过滤）
    cost_per_item: int = 1

    def cost(self) -> int:
        return 0 if self.resource is None else self.items_out * self.cost_per_item


@dataclass(frozen=True)
class FunnelPlan:
    stages: tuple[FunnelStage, ...]
    caps: DailyCaps
    violations: tuple[str, ...] = field(default_factory=tuple)

    @property
    def feasible(self) -> bool:
        return not self.violations

    def total_cost(self, resource: str) -> int:
        return sum(s.cost() for s in self.stages if s.resource == resource)

    def lines(self) -> tuple[str, ...]:
        out = ["漏斗成本核算："]
        for stage in self.stages:
            tag = "零成本" if stage.resource is None else \
                f"{stage.resource} ×{stage.cost()}"
            out.append(f"  {stage.name:<14} {stage.items_in:>7} → "
                       f"{stage.items_out:<7}  {tag}")
        out.append("")
        for resource in ALL_RESOURCES:
            need = self.total_cost(resource)
            cap = self.caps.get(resource)
            mark = "✅" if need <= cap else "🔴"
            out.append(f"  {mark} {resource}: 需要 {need}，硬顶 {cap}")
        out.extend(f"  🔴 {v}" for v in self.violations)
        return tuple(out)


def assert_funnel_feasible(
    stages: Sequence[FunnelStage], caps: DailyCaps
) -> FunnelPlan:
    """启动期检查：漏斗要的量能不能被硬顶容下。

    这条检查存在的理由很具体：设计文档里出现过
    「LLM ≤12 次/天」与「LLM 精评每天约 1000 次调用」并存的情况。
    差 83 倍，两者不可能同真。这类矛盾应当在启动时炸掉，
    而不是等线上跑到第 13 次才失败。
    """
    if not stages:
        raise ValueError("漏斗为空")

    violations: list[str] = []

    for i, stage in enumerate(stages):
        if stage.items_out > stage.items_in:
            violations.append(
                f"「{stage.name}」输出 {stage.items_out} > 输入 {stage.items_in}"
                " —— 漏斗不能变宽"
            )
        if i > 0 and stage.items_in != stages[i - 1].items_out:
            violations.append(
                f"「{stage.name}」输入 {stage.items_in} 与上一级输出 "
                f"{stages[i - 1].items_out} 对不上"
            )

    plan = FunnelPlan(tuple(stages), caps, tuple(violations))

    for resource in ALL_RESOURCES:
        need = plan.total_cost(resource)
        cap = caps.get(resource)
        if need > cap:
            violations.append(
                f"{resource} 需要 {need} 次但硬顶是 {cap} 次 —— 差 "
                f"{need / cap:.0f} 倍，两者不可能同真。"
                "要么提高硬顶，要么把该级的输出量降到 "
                f"{cap // max(next((s.cost_per_item for s in stages if s.resource == resource), 1), 1)} 以内。"
            )

    plan = FunnelPlan(tuple(stages), caps, tuple(violations))
    if not plan.feasible:
        raise BudgetMisconfigured("\n".join(plan.lines()))
    return plan


# ---------------------------------------------------------------------------
# 价值分流
# ---------------------------------------------------------------------------

#: 低于此分位的候选不值得花贵配额。PRIOR。
ESCALATION_PERCENTILE = 0.8


def select_for_escalation(
    scored: Sequence[tuple[str, float]],
    ledger: Ledger,
    resource: str = Resource.LLM,
    cost_per_item: int = 1,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """按分数挑出能进贵通道的候选，剩下的如实标为"未处理"。

    返回 ``(升级处理的 id, 因配额不足未处理的 id)``。

    **不做的事**：不因为配额不够就降低标准去处理更多条，
    也不假装未处理的那些"已评估过"。
    """
    if not scored:
        return (), ()
    if cost_per_item <= 0:
        raise ValueError("单位成本必须为正")

    ordered = sorted(scored, key=lambda p: (-p[1], p[0]))
    affordable = ledger.remaining(resource) // cost_per_item

    escalated = tuple(item_id for item_id, _ in ordered[:affordable])
    skipped = tuple(item_id for item_id, _ in ordered[affordable:])
    return escalated, skipped


@dataclass(frozen=True)
class HonestCount:
    """诚实计数 —— 给界面用的"今天到底处理了多少"。"""

    available: int
    processed: int
    skipped_for_budget: int
    target: int

    @property
    def met_target(self) -> bool:
        return self.processed >= self.target

    def line(self) -> str:
        if self.skipped_for_budget:
            return (f"今日可用 {self.available} 条，实际处理 {self.processed} 条，"
                    f"因配额不足未处理 {self.skipped_for_budget} 条"
                    f"（目标 {self.target} 条）")
        if not self.met_target:
            return (f"今日信息量只有 {self.processed} 条，低于目标 {self.target} 条"
                    " —— 如实推送，不凑数")
        return f"今日处理 {self.processed} 条（目标 {self.target} 条）"


def honest_count(available: int, processed: int, skipped: int,
                 target: int) -> HonestCount:
    if processed + skipped > available:
        raise ValueError(
            f"处理 {processed} + 跳过 {skipped} > 可用 {available} —— 计数不自洽"
        )
    return HonestCount(available, processed, skipped, target)
