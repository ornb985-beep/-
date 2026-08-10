"""贝叶斯分层校准 —— Beta-Binomial + partial pooling。

冷启动的正解：品类内样本很少时，向全局基础率收缩（借力），
样本变多后自动放开。这样从第一条数据起就能给出**诚实的宽区间**，
而不是要么无输出、要么给一个 0/1 极端估计。

    先验    Beta(α₀, β₀)      由全局基础率与"先验等效样本量"决定
    后验    Beta(α₀+k, β₀+n−k)
    收缩    E[p] = (α₀+k) / (α₀+β₀+n)

纯标准库实现：Beta 分位数用二分法 + 正则化不完全 Beta 函数的
连分式展开，不需要 scipy。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from oic.config import MIN_SAMPLES_PER_CATEGORY

#: 先验等效样本量 —— 相当于"在看到任何数据前，我们假装已经观察了这么多次"。
#: 越大收缩越强。PRIOR。
DEFAULT_PRIOR_STRENGTH = 10.0


# ---------------------------------------------------------------------------
# 正则化不完全 Beta 函数（纯标准库）
# ---------------------------------------------------------------------------


def _betacf(a: float, b: float, x: float, max_iter: int = 300, eps: float = 3e-16) -> float:
    """连分式展开（Lentz 算法），Numerical Recipes 标准写法。"""
    tiny = 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """正则化不完全 Beta 函数 I_x(a,b) —— Beta 分布的 CDF。"""
    if not 0.0 <= x <= 1.0:
        raise ValueError("x 必须在 [0,1] 内")
    if a <= 0 or b <= 0:
        raise ValueError("a, b 必须为正")
    if x == 0.0:
        return 0.0
    if x == 1.0:
        return 1.0
    ln_front = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    front = math.exp(ln_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def beta_quantile(a: float, b: float, p: float, tol: float = 1e-10) -> float:
    """Beta 分布分位数 —— 对 CDF 做二分。确定性、无随机成分。"""
    if not 0.0 < p < 1.0:
        raise ValueError("p 必须在 (0,1) 之间")
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if betainc(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# 分层估计
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PooledEstimate:
    category: str
    n: int
    successes: int
    raw_rate: float | None       # 品类内点估计；n=0 时为 None
    pooled_rate: float           # 收缩后的后验均值
    lower: float                 # 后验区间下界
    upper: float
    global_rate: float
    shrinkage: float             # 0=完全用自己数据, 1=完全用全局先验
    borrowed: bool               # 是否处于"主要靠借力"状态
    explanation: tuple[str, ...]


def partial_pool(
    successes_by_category: Mapping[str, tuple[int, int]],
    category: str,
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
    credible_mass: float = 0.90,
    fallback_global_rate: float | None = None,
) -> PooledEstimate:
    """对某品类做 partial pooling 估计。

    ``successes_by_category`` 形如 ``{"户外露营": (成功数, 总数), ...}``。
    ``fallback_global_rate`` 在全局也没有任何数据时使用（赛道先验）。
    """
    if prior_strength <= 0:
        raise ValueError("prior_strength 必须为正")
    if not 0.0 < credible_mass < 1.0:
        raise ValueError("credible_mass 必须在 (0,1) 之间")

    # 全局基础率 —— 按 key 排序遍历，保证确定性
    total_n = 0
    total_k = 0
    for key in sorted(successes_by_category):
        k, n = successes_by_category[key]
        if k < 0 or n < 0 or k > n:
            raise ValueError(f"品类「{key}」计数非法: ({k}, {n})")
        total_k += k
        total_n += n

    if total_n > 0:
        global_rate = total_k / total_n
    elif fallback_global_rate is not None:
        global_rate = fallback_global_rate
    else:
        raise ValueError(
            "全局无任何数据且未提供 fallback_global_rate —— "
            "应返回未知而非编造一个基础率"
        )

    k, n = successes_by_category.get(category, (0, 0))

    alpha0 = prior_strength * global_rate
    beta0 = prior_strength * (1.0 - global_rate)
    # 防止 global_rate 为 0 或 1 时先验退化
    alpha0 = max(alpha0, 1e-6)
    beta0 = max(beta0, 1e-6)

    alpha, beta = alpha0 + k, beta0 + (n - k)
    pooled = alpha / (alpha + beta)

    tail = (1.0 - credible_mass) / 2.0
    lower = beta_quantile(alpha, beta, tail)
    upper = beta_quantile(alpha, beta, 1.0 - tail)

    shrinkage = prior_strength / (prior_strength + n)
    borrowed = n < MIN_SAMPLES_PER_CATEGORY

    lines = [
        f"全局基础率 ō = {global_rate:.4f}（{total_k}/{total_n}）",
        f"品类「{category}」观测 {k}/{n}",
        f"先验 Beta({alpha0:.3f}, {beta0:.3f})（等效样本量 {prior_strength:g}）"
        f" → 后验 Beta({alpha:.3f}, {beta:.3f})",
        f"收缩后估计 = {pooled:.4f}，{credible_mass:.0%} 可信区间 "
        f"[{lower:.4f}, {upper:.4f}]",
        f"收缩强度 = {prior_strength:g}/({prior_strength:g}+{n}) = {shrinkage:.2f}"
        f"（1=完全借全局，0=完全用自己数据）",
    ]
    if borrowed:
        lines.append(
            f"⚠️ 品类内样本 {n} < {MIN_SAMPLES_PER_CATEGORY} —— "
            "该估计主要来自全局借力，区间宽是诚实的，不要当作品类特有结论"
        )

    return PooledEstimate(
        category=category, n=n, successes=k,
        raw_rate=(k / n if n else None),
        pooled_rate=pooled, lower=lower, upper=upper,
        global_rate=global_rate, shrinkage=shrinkage, borrowed=borrowed,
        explanation=tuple(lines),
    )


def base_rate_for_prompt(estimate: PooledEstimate) -> str:
    """给 Analyst 的基础率提示串 —— 强制"先给基础率再调整"。

    依据：标记 comparison class（基础率）的预测平均 Brier = 0.17，
    次好标签仅 0.26。这是实证里最大的单点提升。
    """
    return (
        f"基础率：同类目（{estimate.category}）历史成功率 "
        f"{estimate.pooled_rate:.1%}"
        f"（90% 区间 {estimate.lower:.1%}–{estimate.upper:.1%}，"
        f"样本 n={estimate.n}）。请先以此为锚，再根据本商机的具体证据调整。"
    )
