"""共形预测 —— 有覆盖保证的区间，替代拍脑袋的 P10/P50/P90。

Split conformal 的保证是 distribution-free 且有限样本成立的：
只要校准集与测试点可交换（exchangeable），区间的边际覆盖率
≥ 1 − α。代价是"边际"二字 —— 它不保证对每个子群都成立，
所以提供 Mondrian（按品类分组）变体。

刻意的设计：校准样本不足时**拒绝输出区间**，而不是返回一个
没有任何保证的默认区间。一个没有覆盖保证的"90% 区间"比没有区间更危险。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from oic.config import MIN_SAMPLES_FOR_CALIBRATION


@dataclass(frozen=True)
class Interval:
    lower: float
    upper: float
    alpha: float
    coverage: float          # 1 − α
    n_calibration: int
    guaranteed: bool         # 是否达到有限样本覆盖保证
    note: str

    @property
    def width(self) -> float:
        return self.upper - self.lower


def required_calibration_size(alpha: float) -> int:
    """给定 α，达成有限样本保证所需的最小校准集大小。

    Split conformal 取第 ⌈(n+1)(1−α)⌉ 个残差分位数；
    该下标必须 ≤ n，即 n ≥ ⌈1/α⌉ − 1。
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha 必须在 (0,1) 之间")
    return max(math.ceil(1.0 / alpha) - 1, 1)


def _conformal_quantile(residuals: Sequence[float], alpha: float) -> float:
    """校准残差的 ⌈(n+1)(1−α)⌉/n 经验分位数。

    纯标准库实现：排序后取下标，不需要 numpy。
    """
    n = len(residuals)
    ordered = sorted(residuals)
    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        # 样本不足以支撑该置信水平 —— 退回最保守的最大残差
        return ordered[-1]
    return ordered[k - 1]


def conformal_interval(
    prediction: float,
    calibration_residuals: Sequence[float],
    alpha: float = 0.10,
    clip_to_unit: bool = True,
) -> Interval:
    """Split conformal 区间。

    ``calibration_residuals`` 是校准集上的绝对残差 |预测 − 实际|，
    必须来自**未参与训练**的样本，否则覆盖保证不成立。
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha 必须在 (0,1) 之间")
    if any(r < 0 for r in calibration_residuals):
        raise ValueError("残差必须为绝对值（非负）")

    n = len(calibration_residuals)
    needed = max(required_calibration_size(alpha), MIN_SAMPLES_FOR_CALIBRATION)

    if n < needed:
        return Interval(
            lower=float("nan"), upper=float("nan"), alpha=alpha,
            coverage=1.0 - alpha, n_calibration=n, guaranteed=False,
            note=(f"校准未建立：校准样本 {n} 条 < 所需 {needed} 条。"
                  "拒绝输出区间 —— 无覆盖保证的区间比没有区间更危险。"),
        )

    q = _conformal_quantile(calibration_residuals, alpha)
    lower, upper = prediction - q, prediction + q
    if clip_to_unit:
        lower, upper = max(lower, 0.0), min(upper, 1.0)

    return Interval(
        lower=lower, upper=upper, alpha=alpha, coverage=1.0 - alpha,
        n_calibration=n, guaranteed=True,
        note=(f"Split conformal：{(1-alpha):.0%} 边际覆盖保证，"
              f"校准集 n={n}，残差分位数 q={q:.4f}"),
    )


def mondrian_interval(
    prediction: float,
    category: str,
    residuals_by_category: Mapping[str, Sequence[float]],
    alpha: float = 0.10,
    fallback_to_pooled: bool = True,
) -> Interval:
    """Mondrian（按品类分组）共形区间 —— 保证每个品类各自达标。

    边际覆盖不代表分组覆盖：整体 90% 可能由"A 品类 99% + B 品类 60%"
    构成。做品类间比较时必须用这个变体。
    """
    own = list(residuals_by_category.get(category, ()))
    needed = max(required_calibration_size(alpha), MIN_SAMPLES_FOR_CALIBRATION)

    if len(own) >= needed:
        interval = conformal_interval(prediction, own, alpha)
        return Interval(
            interval.lower, interval.upper, alpha, interval.coverage,
            interval.n_calibration, True,
            f"Mondrian（品类「{category}」内 n={len(own)}）：" + interval.note,
        )

    if not fallback_to_pooled:
        return Interval(
            float("nan"), float("nan"), alpha, 1.0 - alpha, len(own), False,
            f"品类「{category}」校准样本 {len(own)} 条 < {needed} 条，拒绝输出区间。",
        )

    # 合并全部品类做兜底 —— 注意：这样只剩边际保证，不再有分组保证。
    pooled: list[float] = []
    for key in sorted(residuals_by_category):     # 排序保证确定性
        pooled.extend(residuals_by_category[key])
    interval = conformal_interval(prediction, pooled, alpha)
    if not interval.guaranteed:
        return interval
    return Interval(
        interval.lower, interval.upper, alpha, interval.coverage,
        interval.n_calibration, True,
        (f"⚠️ 品类「{category}」样本不足（{len(own)} 条），已退回合并校准集 "
         f"n={interval.n_calibration}。仅剩边际覆盖保证，"
         "不保证该品类内达标。"),
    )
