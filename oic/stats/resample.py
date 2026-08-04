"""重采样推断 —— 小样本下唯一可信的 p 值来源。

为什么不用查表的 t/z 近似：n=6 时正态近似完全失效。
置换检验不假设任何分布，且**在样本小时可以穷举，得到精确 p 值**。

这正是本项目的处境：n=6~8。穷举 C(6,4)=15 种标签排列，
"随机重排后相关性≥观测值"的比例就是精确 p 值 —— 没有近似，没有随机数。
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Sequence

#: 超过这个排列数就改用抽样（固定种子，保证可复现）
MAX_EXACT_PERMUTATIONS = 200_000

#: 抽样置换/Bootstrap 的固定种子 —— 结果必须可复现
SEED = 20260804


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Spearman 秩相关（与 backtest.py 同实现，此处独立以免循环依赖）。"""
    from oic.research.backtest import spearman as _spearman
    return _spearman(list(xs), list(ys))


@dataclass(frozen=True)
class PermutationResult:
    statistic: float
    p_value: float
    n_permutations: int
    exact: bool
    alternative: str

    def line(self) -> str:
        kind = "精确" if self.exact else f"抽样{self.n_permutations}次"
        return (f"统计量 = {self.statistic:+.4f}，p = {self.p_value:.4f}"
                f"（{kind}置换检验，{self.alternative}）")

    def significant(self, alpha: float = 0.05) -> bool:
        return self.p_value <= alpha


def permutation_test_binary(
    values: Sequence[float],
    labels: Sequence[int],
    statistic: Callable[[Sequence[float], Sequence[int]], float] | None = None,
    alternative: str = "two-sided",
) -> PermutationResult:
    """二元标签下的置换检验。

    标签只有 0/1 时，不同排列数 = C(n, k)，k 为 1 的个数。
    n=6、k=4 时只有 15 种 —— **可以穷举，得到精确 p 值**。

    零假设：标签与数值无关，即任何一种标签分配都同样可能。
    """
    if len(values) != len(labels):
        raise ValueError("长度不一致")
    n = len(values)
    if n < 3:
        raise ValueError(f"样本 {n} < 3，置换检验无意义")
    if any(l not in (0, 1) for l in labels):
        raise ValueError("标签必须是 0 或 1")

    k = sum(labels)
    if k == 0 or k == n:
        raise ValueError("标签全同 —— 无法检验")

    stat_fn = statistic or (lambda v, l: spearman(list(v), [float(x) for x in l]))
    observed = stat_fn(values, labels)

    total = math.comb(n, k)
    positions = list(range(n))

    def as_labels(ones: tuple[int, ...]) -> list[int]:
        out = [0] * n
        for i in ones:
            out[i] = 1
        return out

    if total <= MAX_EXACT_PERMUTATIONS:
        stats = [stat_fn(values, as_labels(ones))
                 for ones in combinations(positions, k)]
        exact = True
        n_perm = total
    else:
        rng = random.Random(SEED)
        n_perm = MAX_EXACT_PERMUTATIONS
        stats = []
        for _ in range(n_perm):
            shuffled = list(labels)
            rng.shuffle(shuffled)
            stats.append(stat_fn(values, shuffled))
        exact = False

    if alternative == "two-sided":
        extreme = sum(1 for s in stats if abs(s) >= abs(observed) - 1e-12)
    elif alternative == "greater":
        extreme = sum(1 for s in stats if s >= observed - 1e-12)
    elif alternative == "less":
        extreme = sum(1 for s in stats if s <= observed + 1e-12)
    else:
        raise ValueError(f"未知 alternative: {alternative}")

    # 穷举时观测值本身就在集合里，比例即精确 p 值
    p_value = extreme / len(stats)
    return PermutationResult(observed, p_value, n_perm, exact, alternative)


@dataclass(frozen=True)
class BootstrapCI:
    point: float
    lower: float
    upper: float
    level: float
    n_resamples: int
    n_failed: int

    @property
    def width(self) -> float:
        return self.upper - self.lower

    @property
    def spans_zero(self) -> bool:
        return self.lower <= 0.0 <= self.upper

    def line(self) -> str:
        verdict = "跨越 0，方向不确定" if self.spans_zero else "不跨 0"
        return (f"{self.point:+.4f}，{self.level:.0%} Bootstrap 区间 "
                f"[{self.lower:+.4f}, {self.upper:+.4f}] —— {verdict}")


def bootstrap_ci(
    values: Sequence[float],
    labels: Sequence[int],
    statistic: Callable[[Sequence[float], Sequence[int]], float] | None = None,
    level: float = 0.90,
    n_resamples: int = 5000,
) -> BootstrapCI:
    """百分位 Bootstrap 区间。固定种子，可复现。

    小样本下 Bootstrap 区间会很宽 —— **那是诚实，不是缺陷**。
    宽区间告诉你"这个相关系数根本定不住"，而点值会骗你说定得住。
    """
    if len(values) != len(labels):
        raise ValueError("长度不一致")
    n = len(values)
    if n < 3:
        raise ValueError(f"样本 {n} < 3")

    stat_fn = statistic or (lambda v, l: spearman(list(v), [float(x) for x in l]))
    point = stat_fn(values, labels)

    rng = random.Random(SEED)
    stats: list[float] = []
    failed = 0
    for _ in range(n_resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        sample_v = [values[i] for i in idx]
        sample_l = [labels[i] for i in idx]
        try:
            stats.append(stat_fn(sample_v, sample_l))
        except ValueError:
            # 重采样可能得到全同标签或全并列 —— 统计量无定义，跳过并计数
            failed += 1

    if len(stats) < n_resamples * 0.5:
        raise ValueError(
            f"{failed}/{n_resamples} 次重采样统计量无定义 —— 样本太小或太退化，"
            "Bootstrap 区间不可信"
        )

    stats.sort()
    tail = (1.0 - level) / 2.0
    lower = stats[max(int(tail * len(stats)) - 1, 0)]
    upper = stats[min(int((1.0 - tail) * len(stats)), len(stats) - 1)]
    return BootstrapCI(point, lower, upper, level, n_resamples, failed)
