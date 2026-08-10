"""证据时效衰减与双源锚定。

    w = e^(−λt)      t 单位为天，λ 按品类校准（当前为 PRIOR）

双源锚定四铁律（v3 5.2）：
  1. 同一事件多篇报道按「实体×指标」指纹自动合并，来源数累加
     —— 防止"虚假的多源"（转载十篇同一新闻仍只算一条证据）。
  2. ≥2 个独立来源才算锚定；单源一律标「待核实」。
  3. 来源三级 A/B/C；C 只作线索不作证据。
  4. 媒体数字与官方统计偏差 >30% 自动降权。
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from oic.config import (
    DEFAULT_DECAY_LAMBDA,
    MIN_INDEPENDENT_SOURCES,
    SOURCE_DIVERGENCE_LIMIT,
)


def decay_weight(age_days: float, lam: float = DEFAULT_DECAY_LAMBDA) -> float:
    """指数衰减权重。age_days 为负（未来时间戳）时报错而非静默放大。"""
    if age_days < 0:
        raise ValueError("证据年龄不能为负 —— 时间戳有误")
    if lam < 0:
        raise ValueError("λ 不能为负")
    return math.exp(-lam * age_days)


def half_life_days(lam: float = DEFAULT_DECAY_LAMBDA) -> float:
    """把 λ 翻译成人能理解的半衰期。"""
    if lam <= 0:
        return float("inf")
    return math.log(2.0) / lam


@dataclass(frozen=True)
class Datum:
    """一条来自某来源的「实体×指标」观测。"""

    entity: str
    metric: str
    value: float
    source_id: str        # 用于判断独立性：同一 source_id 视为同一来源
    grade: str            # A / B / C
    age_days: float
    url: str = ""


def fingerprint(entity: str, metric: str) -> str:
    """「实体×指标」指纹 —— 转载合并的键。"""
    digest = hashlib.sha256()
    digest.update(entity.strip().casefold().encode("utf-8"))
    digest.update(b"\x1f")
    digest.update(metric.strip().casefold().encode("utf-8"))
    return digest.hexdigest()[:16]


@dataclass(frozen=True)
class AnchorResult:
    fingerprint: str
    entity: str
    metric: str
    independent_sources: int
    grades: tuple[str, ...]
    anchored: bool
    official_value: float | None
    consensus_value: float | None
    divergent: bool
    weight: float
    status: str
    explanation: tuple[str, ...]


def anchor(data: Sequence[Datum], lam: float = DEFAULT_DECAY_LAMBDA) -> AnchorResult:
    """对同一「实体×指标」的多条观测做双源锚定。

    独立来源数按 ``source_id`` 去重 —— 十篇转载同一通稿只算一条。
    """
    if not data:
        raise ValueError("观测为空 —— 应返回未知而非默认值")

    entities = {d.entity for d in data}
    metrics = {d.metric for d in data}
    if len(entities) != 1 or len(metrics) != 1:
        raise ValueError("anchor() 只接受同一「实体×指标」的观测")

    entity = data[0].entity
    metric = data[0].metric
    fp = fingerprint(entity, metric)

    # 按 source_id 去重，保留每个来源最新的一条
    by_source: dict[str, Datum] = {}
    for datum in data:
        existing = by_source.get(datum.source_id)
        if existing is None or datum.age_days < existing.age_days:
            by_source[datum.source_id] = datum

    unique = [by_source[key] for key in sorted(by_source)]   # 排序保证确定性
    n_independent = len(unique)
    grades = tuple(sorted(d.grade for d in unique))

    # 铁律 3：C 级只作线索
    evidential = [d for d in unique if d.grade in ("A", "B")]
    anchored = len(evidential) >= MIN_INDEPENDENT_SOURCES

    official = next((d.value for d in unique if d.grade == "A"), None)

    # 加权共识值：来源等级 × 时效衰减
    grade_weight = {"A": 1.0, "B": 0.6, "C": 0.0}
    numerator = 0.0
    denominator = 0.0
    for datum in unique:
        w = grade_weight[datum.grade] * decay_weight(datum.age_days, lam)
        numerator += w * datum.value
        denominator += w
    consensus = numerator / denominator if denominator > 0 else None

    # 铁律 4：媒体数字与官方偏差 >30% 降权
    divergent = False
    if official is not None and official != 0:
        for datum in unique:
            if datum.grade == "B":
                if abs(datum.value - official) / abs(official) > SOURCE_DIVERGENCE_LIMIT:
                    divergent = True
                    break

    freshest = min(d.age_days for d in unique)
    weight = decay_weight(freshest, lam)
    if divergent:
        weight *= 0.5

    if not anchored:
        status = "待核实"
    elif divergent:
        status = "已锚定（有口径冲突）"
    else:
        status = "已锚定"

    lines = [
        f"「{entity} × {metric}」指纹 {fp}",
        f"独立来源 {n_independent} 个（等级 {'/'.join(grades)}），"
        f"其中 A/B 级 {len(evidential)} 个",
        f"最新证据 {freshest:g} 天前，时效权重 {weight:.4f}"
        f"（半衰期 {half_life_days(lam):.0f} 天）",
        f"状态：{status}",
    ]
    if not anchored:
        lines.append(
            f"⚠️ A/B 级独立来源不足 {MIN_INDEPENDENT_SOURCES} 个 —— "
            "标「待核实」，不得作为结论依据"
        )
    if divergent:
        lines.append(
            f"⚠️ 媒体数字与官方统计偏差 >{SOURCE_DIVERGENCE_LIMIT:.0%} —— "
            "自动降权。不要强行平均，应解释口径差异并提出最小验证动作。"
        )
    if consensus is None:
        lines.append("⚠️ 全部为 C 级来源 —— 无共识值，仅作线索")

    return AnchorResult(
        fingerprint=fp, entity=entity, metric=metric,
        independent_sources=n_independent, grades=grades, anchored=anchored,
        official_value=official, consensus_value=consensus, divergent=divergent,
        weight=weight, status=status, explanation=tuple(lines),
    )


def group_by_fingerprint(data: Iterable[Datum]) -> dict[str, list[Datum]]:
    """按「实体×指标」分组 —— 合并转载的入口。"""
    groups: dict[str, list[Datum]] = {}
    for datum in data:
        groups.setdefault(fingerprint(datum.entity, datum.metric), []).append(datum)
    return groups
