"""概率聚合 —— logit pooling + extremization。

为什么不用算术平均：多个独立预测者各自基于**部分**信息作判断，
简单平均会把他们共有的不确定性重复计入，结果系统性地"欠自信"
（向 0.5 收缩）。GJP 的做法是在 logit 空间平均后再向外拉伸
(extremize)，把"多个独立来源都指向同一方向"这件事的信息量还回来。

这是"团队比个人准确约 23%"的正确实现方式 —— v3 只记了结论，
没给公式。

同时提供分歧度指标：多 agent 分歧大本身就是免费的不确定性估计，
应触发降置信度 + 强制人审，而不是被平均掉。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

#: 概率裁剪边界 —— 防止 logit 发散到 ±inf。
#: 也隐含一条纪律：永不输出 0% 或 100%。
EPSILON = 1e-6

#: extremization 系数。a=1 退化为纯 logit 平均；GJP 实践中常用 1.5–2.5。
#: PRIOR —— 最优 a 依赖预测者独立性，必须用真实 Outcome 校准。
DEFAULT_EXTREMIZE_A = 1.5

#: 分歧度超过此值即强制人审（logit 标准差，PRIOR）
DISAGREEMENT_THRESHOLD = 1.0


def _clip(p: float) -> float:
    return min(max(p, EPSILON), 1.0 - EPSILON)


def logit(p: float) -> float:
    p = _clip(p)
    return math.log(p / (1.0 - p))


def inv_logit(z: float) -> float:
    # 数值稳定写法，避免 exp 溢出
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


@dataclass(frozen=True)
class Aggregation:
    probability: float
    naive_mean: float
    logit_mean: float
    disagreement: float          # logit 空间标准差
    requires_human_review: bool
    n_sources: int
    explanation: tuple[str, ...]


def aggregate_probabilities(
    probabilities: Sequence[float],
    weights: Sequence[float] | None = None,
    extremize_a: float = DEFAULT_EXTREMIZE_A,
    disagreement_threshold: float = DISAGREEMENT_THRESHOLD,
) -> Aggregation:
    """加权 logit 平均后做 extremization。

        z_i  = logit(p_i)
        z̄   = Σ w_i z_i / Σ w_i
        p*  = inv_logit(a · z̄)

    ``a > 1`` 把结果推离 0.5；``a = 1`` 即纯 logit 平均。
    """
    if not probabilities:
        raise ValueError("概率列表为空 —— 应返回未知而非默认值")
    if extremize_a <= 0:
        raise ValueError("extremize_a 必须为正")

    n = len(probabilities)
    if weights is None:
        weights = [1.0] * n
    if len(weights) != n:
        raise ValueError("weights 长度必须与 probabilities 一致")
    if any(w < 0 for w in weights):
        raise ValueError("权重不能为负")
    weight_sum = sum(weights)
    if weight_sum <= 0:
        raise ValueError("权重之和必须为正")

    for p in probabilities:
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"概率必须在 0–1 之间，收到 {p}")

    zs = [logit(p) for p in probabilities]
    z_mean = sum(w * z for w, z in zip(weights, zs)) / weight_sum

    # 加权总体标准差作为分歧度
    variance = sum(w * (z - z_mean) ** 2 for w, z in zip(weights, zs)) / weight_sum
    disagreement = math.sqrt(variance)

    pooled = inv_logit(extremize_a * z_mean)
    naive = sum(w * p for w, p in zip(weights, probabilities)) / weight_sum

    needs_review = disagreement > disagreement_threshold

    lines = [
        f"logit 均值 z̄ = {z_mean:.4f}（{n} 个来源）",
        f"extremize a={extremize_a:g} → p* = inv_logit({extremize_a:g}×{z_mean:.4f})"
        f" = {pooled:.4f}",
        f"（朴素算术平均为 {naive:.4f}，差值 {pooled - naive:+.4f}）",
        f"分歧度（logit 标准差）= {disagreement:.4f}",
    ]
    if needs_review:
        lines.append(
            f"⚠️ 分歧度 {disagreement:.2f} > {disagreement_threshold:g} —— "
            "来源判断严重不一致，强制人工终审，不要相信聚合值"
        )
    return Aggregation(
        probability=pooled,
        naive_mean=naive,
        logit_mean=z_mean,
        disagreement=disagreement,
        requires_human_review=needs_review,
        n_sources=n,
        explanation=tuple(lines),
    )


def round_to_percent(p: float) -> float:
    """概率粒度化 —— 超预最常报 1% 的倍数，普通人报 10% 的倍数。

    允许 63% 而不是只能报 60%。这是可直接编码的超预行为规则。
    """
    return round(p * 100.0) / 100.0
