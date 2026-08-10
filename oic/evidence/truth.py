"""真值发现 —— 来源可信度与真值的联合估计。

替代"按手工 A/B/C 等级加权平均"。核心思想（CRH / TruthFinder 一族）：

    可信的来源 = 报的值接近真值的来源
    真值       = 可信来源共同指向的值

两者互为条件，用迭代求解。这样来源权重是**学出来的**，
而不是拍脑袋分级 —— 一个自称"官方"但数字长期离谱的源会被自动降权。

刻意的克制：
  * 迭代次数固定、初值固定 → 完全确定性，不破坏 verify_scores；
  * 来源数 <3 时直接退回等级加权，因为此时"学"出来的权重毫无意义。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

#: 来源数低于此值时不做真值发现 —— 样本太少，学出来的权重是噪声
MIN_SOURCES_FOR_DISCOVERY = 3

#: 固定迭代次数，保证确定性（不用收敛判据，避免浮点边界导致的分支差异）
ITERATIONS = 20

#: 防止单一来源权重发散
MAX_WEIGHT = 10.0


@dataclass(frozen=True)
class Observation:
    source_id: str
    value: float


@dataclass(frozen=True)
class TruthEstimate:
    value: float
    source_weights: tuple[tuple[str, float], ...]   # 排序后的 (source_id, weight)
    n_sources: int
    method: str
    explanation: tuple[str, ...]


def _weighted_median(pairs: Sequence[tuple[float, float]]) -> float:
    """加权中位数 —— 比加权均值抗离群点（一个刷出来的数字不会拖走真值）。"""
    ordered = sorted(pairs, key=lambda p: p[0])
    total = sum(w for _, w in ordered)
    if total <= 0:
        raise ValueError("权重之和必须为正")
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= total / 2.0:
            return value
    return ordered[-1][0]


def discover(
    observations: Sequence[Observation],
    prior_weights: Mapping[str, float] | None = None,
    iterations: int = ITERATIONS,
) -> TruthEstimate:
    """迭代估计真值与来源可信度。

    ``prior_weights`` 可传入等级先验（如 A=1.0, B=0.6, C=0.2）作为起点。
    """
    if not observations:
        raise ValueError("观测为空 —— 应返回未知而非默认值")

    # 同一来源多条时取其中位数，避免刷条数抬高影响力
    by_source: dict[str, list[float]] = {}
    for obs in observations:
        by_source.setdefault(obs.source_id, []).append(obs.value)

    source_ids = sorted(by_source)             # 排序保证确定性
    values = {
        sid: sorted(by_source[sid])[len(by_source[sid]) // 2] for sid in source_ids
    }
    n = len(source_ids)

    weights = {
        sid: (prior_weights.get(sid, 1.0) if prior_weights else 1.0)
        for sid in source_ids
    }

    if n < MIN_SOURCES_FOR_DISCOVERY:
        pairs = [(values[sid], max(weights[sid], 0.0)) for sid in source_ids]
        total = sum(w for _, w in pairs)
        if total <= 0:
            raise ValueError("全部来源权重为 0 —— 无共识值")
        estimate = _weighted_median(pairs)
        return TruthEstimate(
            estimate,
            tuple((sid, weights[sid]) for sid in source_ids),
            n, "prior_weighted",
            (f"来源数 {n} < {MIN_SOURCES_FOR_DISCOVERY} —— 不做真值发现，"
             "退回等级加权中位数。样本太少时学出的可信度是噪声。",),
        )

    truth = _weighted_median([(values[sid], max(weights[sid], 1e-9)) for sid in source_ids])
    scale = max(
        (max(values.values()) - min(values.values())) / 2.0,
        abs(truth) * 0.05,
        1e-9,
    )

    for _ in range(iterations):
        # 来源可信度 ← 与当前真值的距离
        for sid in source_ids:
            error = abs(values[sid] - truth) / scale
            weights[sid] = min(math.exp(-error), MAX_WEIGHT)
        total = sum(weights[sid] for sid in source_ids)
        if total <= 0:
            break
        # 真值 ← 可信来源的加权中位数
        truth = _weighted_median([(values[sid], weights[sid]) for sid in source_ids])

    ranked = tuple(sorted(
        ((sid, weights[sid]) for sid in source_ids),
        key=lambda p: (-p[1], p[0]),
    ))

    lines = [
        f"真值发现（{n} 个独立来源，{iterations} 次迭代）→ {truth:g}",
        "来源可信度（学习所得，非人工分级）：",
    ]
    lines.extend(f"    {sid}: {w:.4f}（报 {values[sid]:g}）" for sid, w in ranked)
    outliers = [sid for sid, w in ranked if w < 0.3]
    if outliers:
        lines.append(
            f"⚠️ 低可信来源：{'、'.join(outliers)} —— 其数值远离共识，"
            "应人工核查是口径差异还是数据污染"
        )

    return TruthEstimate(truth, ranked, n, "truth_discovery", tuple(lines))
