"""品类档案 —— 把散落的观测组织成可评分的输入。

流程：
    原始观测 → as-of 时间闸 → 按口径分组 → 双源锚定 / 真值发现 → 品类档案

每一步都可能**拒绝输出**：口径冲突拒绝合并、时间越界拒绝放行、
来源不足拒绝锚定。拒绝比给一个看似精确的错数字有价值。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from oic.evidence import truth
from oic.evidence.decay import Datum, anchor
from oic.research import metrics as mx
from oic.research.asof import assert_no_lookahead, coverage, filter_available
from oic.research.units import Currency, Quantity


@dataclass(frozen=True)
class Observation:
    """一条从检索里提取的观测。

    ``snippet`` 存原文片段 —— 这是可审计性的基础：
    任何人都能拿 source_url + snippet 复查我有没有编数字。
    """

    category_key: str
    metric_family: str
    metric_scope: str
    metric_measure: str
    year: int
    value: float
    currency: str
    unit_note: str
    source_url: str
    source_name: str
    source_grade: str            # A 官方/财报 · B 权威媒体 · C 自媒体
    published_at: str            # ISO；决定能否过 as-of 闸
    retrieved_at: str
    snippet: str
    converted: bool = False

    @property
    def metric_key(self) -> mx.MetricKey:
        return mx.MetricKey(self.metric_family, self.metric_scope, self.metric_measure)

    def to_datum(self, as_of_year: int) -> Datum:
        """转成 evidence.decay.Datum 以复用双源锚定。

        ``age_days`` 用年差近似（观测多为年度数据，没有精确日期）。
        """
        age_days = max((as_of_year - self.year) * 365.0, 0.0)
        return Datum(
            entity=self.category_key,
            metric=self.metric_key.label(),
            value=self.value,
            source_id=self.source_name,
            grade=self.source_grade,
            age_days=age_days,
            url=self.source_url,
        )


def load_observations(path: Path) -> list[Observation]:
    records: list[Observation] = []
    if not path.exists():
        return records
    with path.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                records.append(Observation(**json.loads(line)))
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError(f"{path}:{lineno} 解析失败: {exc}") from exc
    return records


def save_observations(path: Path, observations: Sequence[Observation],
                      header: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        if header:
            for line in header.splitlines():
                handle.write(f"// {line}\n")
        for obs in observations:
            handle.write(json.dumps(asdict(obs), ensure_ascii=False,
                                    sort_keys=True, separators=(",", ":")) + "\n")


@dataclass(frozen=True)
class Resolved:
    """某个 (口径, 年份) 上的共识值。"""

    metric_key: mx.MetricKey
    year: int
    value: float | None
    n_sources: int
    anchored: bool
    method: str
    note: str
    explanation: tuple[str, ...] = field(default_factory=tuple)


def resolve(observations: Sequence[Observation], as_of_year: int) -> Resolved:
    """把同一 (品类, 口径, 年份) 的多条观测归一成一个值。

    **口径不同直接抛 MetricConflict** —— 不做降权，不做平均。
    """
    if not observations:
        raise ValueError("观测为空 —— 返回未知而非默认值")

    key = mx.assert_mergeable([o.metric_key for o in observations])
    years = {o.year for o in observations}
    if len(years) != 1:
        raise ValueError(f"年份不一致: {sorted(years)} —— 不同年份不可合并")
    year = observations[0].year

    # 币种必须一致（调用方应先 to_cny）
    currencies = {o.currency for o in observations}
    if len(currencies) > 1:
        raise ValueError(
            f"币种不一致: {sorted(currencies)} —— 请先统一折算并标记 converted"
        )

    data = [o.to_datum(as_of_year) for o in observations]
    anchor_result = anchor(data)

    if len(observations) >= truth.MIN_SOURCES_FOR_DISCOVERY:
        estimate = truth.discover(
            [truth.Observation(o.source_name, o.value) for o in observations]
        )
        value, method = estimate.value, estimate.method
        explanation = anchor_result.explanation + estimate.explanation
    else:
        value = anchor_result.consensus_value
        method = "anchor_weighted"
        explanation = anchor_result.explanation

    return Resolved(
        metric_key=key, year=year, value=value,
        n_sources=anchor_result.independent_sources,
        anchored=anchor_result.anchored,
        method=method,
        note=anchor_result.status,
        explanation=explanation,
    )


@dataclass(frozen=True)
class CategoryDossier:
    category_key: str
    category_name: str
    as_of: str
    resolved: dict[str, Resolved]        # "family/scope/measure@year" → Resolved
    n_observations_total: int
    n_observations_used: int
    conflicts: tuple[str, ...]

    def get(self, key: mx.MetricKey, year: int) -> Resolved | None:
        return self.resolved.get(f"{key.label()}@{year}")

    def value(self, key: mx.MetricKey, year: int) -> float | None:
        found = self.get(key, year)
        return found.value if found else None

    def growth_pct(self, key: mx.MetricKey, year: int, prior_year: int) -> float | None:
        """从两年的存量算增速。任一年缺失即返回 None —— 不外推。"""
        now = self.value(key, year)
        before = self.value(key, prior_year)
        if now is None or before is None or before == 0:
            return None
        return (now - before) / before * 100.0

    def summary(self) -> tuple[str, ...]:
        lines = [
            f"【{self.category_name}】as-of {self.as_of}",
            f"观测 {self.n_observations_used}/{self.n_observations_total} 条通过时间闸",
        ]
        for label in sorted(self.resolved):
            item = self.resolved[label]
            shown = "未知" if item.value is None else f"{item.value:,.4g}"
            flag = "" if item.anchored else "  ⚠️待核实"
            lines.append(f"  {label:<44} {shown:>16}  "
                         f"({item.n_sources}源/{item.method}){flag}")
        lines.extend(f"  ⚠️ {c}" for c in self.conflicts)
        return tuple(lines)


def build_dossier(
    category_key: str,
    category_name: str,
    observations: Sequence[Observation],
    as_of: str,
    enforce_gate: bool = True,
) -> CategoryDossier:
    """按 as-of 建档。

    ``enforce_gate=True`` 时，任何晚于 as-of 的观测会**抛错**而不是被静默丢弃 ——
    因为它出现在这里本身就说明采集流程有问题。
    结局侧建档用 ``enforce_gate=False``。
    """
    mine = [o for o in observations if o.category_key == category_key]

    if enforce_gate:
        for obs in mine:
            assert_no_lookahead(
                obs.published_at, as_of,
                f"{category_name}/{obs.metric_key.label()}@{obs.year}",
            )
        usable = mine
    else:
        usable = list(mine)

    as_of_year = int(as_of.split("-")[0])

    # 按 (口径, 年份) 分桶
    buckets: dict[str, list[Observation]] = {}
    for obs in usable:
        buckets.setdefault(f"{obs.metric_key.label()}@{obs.year}", []).append(obs)

    resolved: dict[str, Resolved] = {}
    conflicts: list[str] = []
    for label in sorted(buckets):
        try:
            resolved[label] = resolve(buckets[label], as_of_year)
        except mx.MetricConflict as exc:
            conflicts.append(str(exc).splitlines()[0])
        except ValueError as exc:
            conflicts.append(f"{label}: {exc}")

    return CategoryDossier(
        category_key=category_key,
        category_name=category_name,
        as_of=as_of,
        resolved=resolved,
        n_observations_total=len(mine),
        n_observations_used=len(usable),
        conflicts=tuple(conflicts),
    )
