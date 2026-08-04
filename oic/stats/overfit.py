"""回测过拟合检测 —— 本仓库里最重要的一个"扫兴"模块。

核心事实：**在 n=8 上测 20 个特征，最好的那个必然好看，纯属偶然。**

这是量化金融最贵的教训。无数策略在回测里漂亮、上线即死，
原因几乎都是同一个：试了很多组合，只报了最好的那个，
却用"仿佛只试过一次"的标准去判断显著性。

本模块提供三件工具：

    expected_max_correlation  试 k 次，纯运气能得到多大的 |ρ|？
    benjamini_hochberg        多重检验校正，控制错误发现率
    probability_of_overfit    PBO：样本内最优在样本外掉到中位数以下的概率

对本项目的直接含义：上一轮 ρ=−0.293（n=6）。若我接着测剪刀差、
切换势能、HHI、成熟度…共 20 个特征，`expected_max_correlation`
会告诉我纯运气就能刷出多大的值 —— 若观测值没超过它，就什么都没发现。
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

SEED = 20260804


# ---------------------------------------------------------------------------
# 一、试 k 次，运气能给多大的相关性
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LuckBaseline:
    n_samples: int
    n_features: int
    median_max_abs_rho: float
    p95_max_abs_rho: float
    n_simulations: int

    def beats_luck(self, observed_abs_rho: float) -> bool:
        return observed_abs_rho > self.p95_max_abs_rho

    def lines(self, observed_abs_rho: float | None = None) -> tuple[str, ...]:
        out = [
            f"在 n={self.n_samples}、试 {self.n_features} 个特征的条件下，"
            "纯随机能刷出的最大 |ρ|：",
            f"    中位数 {self.median_max_abs_rho:.3f}，"
            f"95 分位 {self.p95_max_abs_rho:.3f}",
        ]
        if observed_abs_rho is not None:
            if self.beats_luck(observed_abs_rho):
                out.append(f"    观测 |ρ|={observed_abs_rho:.3f} 超过运气 95 分位 —— 值得继续查")
            else:
                out.append(
                    f"    观测 |ρ|={observed_abs_rho:.3f} **没有超过**运气 95 分位 "
                    f"{self.p95_max_abs_rho:.3f} —— 无法与偶然区分"
                )
        return tuple(out)


def expected_max_correlation(
    n_samples: int,
    n_features: int,
    n_simulations: int = 2000,
) -> LuckBaseline:
    """模拟：在完全无关的数据上试 k 个特征，最大 |ρ| 的分布。

    这是"多重比较"最直观的表达方式 —— 比 p 值更容易让人理解为什么
    "我们测了 20 个指标，发现 X 最相关"通常什么都没发现。
    """
    if n_samples < 3:
        raise ValueError("样本至少 3 个")
    if n_features < 1:
        raise ValueError("特征至少 1 个")

    from oic.research.backtest import spearman

    rng = random.Random(SEED)
    maxima: list[float] = []
    # 标签固定为均衡二元，模拟真实场景
    labels = [1 if i < n_samples // 2 else 0 for i in range(n_samples)]

    for _ in range(n_simulations):
        best = 0.0
        for _ in range(n_features):
            noise = [rng.gauss(0.0, 1.0) for _ in range(n_samples)]
            try:
                rho = spearman(noise, [float(x) for x in labels])
            except ValueError:
                continue
            best = max(best, abs(rho))
        maxima.append(best)

    maxima.sort()
    median = maxima[len(maxima) // 2]
    p95 = maxima[min(int(0.95 * len(maxima)), len(maxima) - 1)]
    return LuckBaseline(n_samples, n_features, median, p95, n_simulations)


# ---------------------------------------------------------------------------
# 二、多重检验校正
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CorrectedTest:
    name: str
    p_value: float
    adjusted_p: float
    rejected: bool


def benjamini_hochberg(
    named_p_values: Sequence[tuple[str, float]], alpha: float = 0.05
) -> tuple[CorrectedTest, ...]:
    """Benjamini-Hochberg 错误发现率控制。

    比 Bonferroni 温和：Bonferroni 控制"至少一个假阳性"的概率，
    在特征多时过于保守；BH 控制"报出来的里面有多少是假的"，更贴合选特征的场景。
    """
    if not named_p_values:
        raise ValueError("检验列表为空")
    for name, p in named_p_values:
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"{name} 的 p 值非法: {p}")

    m = len(named_p_values)
    ordered = sorted(named_p_values, key=lambda t: t[1])

    # 单调化的调整 p 值：从大到小取累积最小
    adjusted: list[float] = [0.0] * m
    running = 1.0
    for i in range(m - 1, -1, -1):
        value = ordered[i][1] * m / (i + 1)
        running = min(running, value)
        adjusted[i] = min(running, 1.0)

    return tuple(
        CorrectedTest(name, p, adjusted[i], adjusted[i] <= alpha)
        for i, (name, p) in enumerate(ordered)
    )


# ---------------------------------------------------------------------------
# 三、PBO（回测过拟合概率）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OverfitReport:
    pbo: float
    n_splits: int
    n_strategies: int
    n_observations: int
    note: str

    @property
    def severe(self) -> bool:
        return self.pbo >= 0.5

    def lines(self) -> tuple[str, ...]:
        out = [
            f"PBO = **{self.pbo:.1%}**"
            f"（{self.n_strategies} 个候选 × {self.n_observations} 个样本，"
            f"{self.n_splits} 次组合切分）",
            "含义：样本内表现最好的那个，在样本外掉到中位数以下的概率。",
        ]
        if self.severe:
            out.append(
                "🔴 PBO ≥ 50% —— 选出来的「最优」有一半以上概率是拟合噪声。"
                "此时任何「我们找到了有效信号」的宣称都不成立。"
            )
        else:
            out.append("🟡 PBO < 50%，但小样本下这个估计本身也不稳，别当保证。")
        out.append(self.note)
        return tuple(out)


def probability_of_overfit(
    performance: Sequence[Sequence[float]],
    n_splits: int = 8,
) -> OverfitReport:
    """CSCV 法估计回测过拟合概率（López de Prado 一族方法）。

    ``performance[i][t]`` = 第 i 个候选策略在第 t 个观测上的表现。

    做法：把时间轴切成 S 块，穷举所有"一半训练一半测试"的组合。
    每次在训练半找表现最好的策略，看它在测试半的排名。
    **若"样本内最优"在样本外经常掉到中位数以下，说明选优在拟合噪声。**
    """
    if not performance:
        raise ValueError("候选策略为空")
    n_strategies = len(performance)
    if n_strategies < 2:
        raise ValueError("至少需要 2 个候选策略才能谈「选优」")

    n_obs = len(performance[0])
    if any(len(row) != n_obs for row in performance):
        raise ValueError("各策略的观测数必须一致")

    # 切块数不能超过观测数，且必须为偶数才能对半分
    n_splits = min(n_splits, n_obs)
    if n_splits % 2 == 1:
        n_splits -= 1
    if n_splits < 2:
        raise ValueError(f"观测数 {n_obs} 太少，无法做组合切分")

    block_size = n_obs // n_splits
    blocks = [list(range(i * block_size,
                         (i + 1) * block_size if i < n_splits - 1 else n_obs))
              for i in range(n_splits)]

    half = n_splits // 2
    below_median = 0
    total = 0

    for train_blocks in combinations(range(n_splits), half):
        train_idx = [i for b in train_blocks for i in blocks[b]]
        test_idx = [i for b in range(n_splits) if b not in train_blocks
                    for i in blocks[b]]
        if not train_idx or not test_idx:
            continue

        def mean_on(row: Sequence[float], idx: list[int]) -> float:
            return sum(row[i] for i in idx) / len(idx)

        train_scores = [mean_on(row, train_idx) for row in performance]
        best = max(range(n_strategies), key=lambda i: train_scores[i])

        test_scores = [mean_on(row, test_idx) for row in performance]
        ordered = sorted(range(n_strategies), key=lambda i: test_scores[i])
        rank = ordered.index(best)                      # 0 = 最差
        relative = rank / (n_strategies - 1)            # 0..1

        if relative < 0.5:
            below_median += 1
        total += 1

    if total == 0:
        raise ValueError("无有效切分")

    pbo = below_median / total
    note = ("注：n 很小时 PBO 本身方差极大，应当作方向性提示。"
            if n_obs < 30 else "")
    return OverfitReport(pbo, total, n_strategies, n_obs, note)


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------


def _selftest() -> int:
    failures = 0

    def check(label: str, ok: bool) -> None:
        nonlocal failures
        if not ok:
            failures += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    print("oic.stats.overfit 自检\n")

    # 试得越多，运气能刷出的最大值越大
    one = expected_max_correlation(8, 1, n_simulations=400)
    twenty = expected_max_correlation(8, 20, n_simulations=400)
    check("试 20 个特征比试 1 个更容易撞出高 |ρ|",
          twenty.p95_max_abs_rho > one.p95_max_abs_rho)
    print(f"      n=8 试1个：95分位 |ρ|={one.p95_max_abs_rho:.3f}")
    print(f"      n=8 试20个：95分位 |ρ|={twenty.p95_max_abs_rho:.3f}")

    check("本项目实际值 |ρ|=0.293 打不过 n=8 试20个的运气基线",
          not twenty.beats_luck(0.293))

    # BH 校正
    tests = [("a", 0.001), ("b", 0.04), ("c", 0.30), ("d", 0.80)]
    corrected = benjamini_hochberg(tests, alpha=0.05)
    check("BH 调整后 p 值不小于原始 p 值",
          all(c.adjusted_p >= c.p_value - 1e-12 for c in corrected))
    check("最显著的仍被拒绝原假设", corrected[0].rejected)
    check("边缘显著的 p=0.04 经校正后不再显著",
          not [c for c in corrected if c.name == "b"][0].rejected)

    try:
        benjamini_hochberg([("x", 1.5)])
        check("非法 p 值抛错", False)
    except ValueError:
        check("非法 p 值抛错", True)

    # PBO：纯噪声策略应给出高 PBO
    rng = random.Random(1)
    noise = [[rng.gauss(0, 1) for _ in range(32)] for _ in range(20)]
    noise_report = probability_of_overfit(noise, n_splits=8)
    check(f"20个纯噪声策略 PBO={noise_report.pbo:.0%} 应偏高(≥0.35)",
          noise_report.pbo >= 0.35)

    # 一个真有效的策略应给出低 PBO
    good = [[rng.gauss(0, 1) for _ in range(32)] for _ in range(19)]
    good.append([2.0 + rng.gauss(0, 0.1) for _ in range(32)])   # 明显更优
    good_report = probability_of_overfit(good, n_splits=8)
    check(f"存在真优策略时 PBO={good_report.pbo:.0%} 应很低(<0.2)",
          good_report.pbo < 0.2)

    try:
        probability_of_overfit([[1.0, 2.0]])
        check("单一策略时抛错", False)
    except ValueError:
        check("单一策略时抛错", True)

    print(f"\n{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
