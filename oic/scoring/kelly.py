"""Kelly 仓位 —— "高胜率反复下小注"的数学形式。

⚠️ 这个模块最危险，因此安全阀写在最前面。

Kelly 公式 f* = (bp − q)/b 只在 **p 已知** 时最优。现实中 p 是估计的，
而 Kelly 对 p 的高估极度不对称地敏感：把真实 20% 的胜率误估为 40%，
长期增长率会变成负数 —— 也就是这个函数会主动让用户破产。

因此三重安全阀，全部不可关闭：
  1. 只用胜率区间的**下界**（Wilson score lower bound），不用点估计；
  2. 硬上限 ¼ Kelly；
  3. 样本 < MIN_SAMPLES_FOR_CALIBRATION 时**拒绝输出仓位**。

第 3 条意味着：在 Outcome 表为空的现在，这个函数永远返回"拒绝"。
这是正确行为，不是缺陷。
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

from oic.config import MIN_SAMPLES_FOR_CALIBRATION

#: 分数 Kelly 上限。全 Kelly 的回撤在实践中无法承受，
#: 且对参数误差极敏感；¼ Kelly 保留约 3/4 的增长率而大幅降低方差。
MAX_KELLY_FRACTION = 0.25

#: Wilson 区间的置信水平对应的 z 值（90% 单侧 ≈ 1.2816）
WILSON_Z = 1.2816


@dataclass(frozen=True)
class Position:
    fraction: float | None       # 建议投入占可用测试预算的比例；None = 拒绝
    amount: float | None         # 折算金额
    win_rate_point: float | None
    win_rate_lower: float | None
    raw_kelly: float | None
    n_samples: int
    refused: bool
    reason: str
    explanation: tuple[str, ...]


def wilson_lower_bound(wins: int, trials: int, z: float = WILSON_Z) -> float:
    """Wilson score 区间下界 —— 小样本下比正态近似稳健得多。

    用下界而非点估计，是 Kelly 安全阀的第一道：
    宁可少下注，不可高估胜率。
    """
    if trials <= 0:
        raise ValueError("trials 必须为正")
    if not 0 <= wins <= trials:
        raise ValueError("wins 必须在 0..trials 之间")

    n = float(trials)
    p_hat = wins / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    center = p_hat + z2 / (2.0 * n)
    margin = z * math.sqrt(p_hat * (1.0 - p_hat) / n + z2 / (4.0 * n * n))
    return max((center - margin) / denominator, 0.0)


def raw_kelly_fraction(p: float, payoff_b: float) -> float:
    """f* = (b·p − q) / b，其中 q = 1 − p。

    ``payoff_b`` 是赔率：赢时净赚为本金的 b 倍。
    结果可能为负 —— 负值表示这是负期望赌局，不该下注。
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError("胜率必须在 0–1 之间")
    if payoff_b <= 0:
        raise ValueError("赔率 b 必须为正")
    q = 1.0 - p
    return (payoff_b * p - q) / payoff_b


def position_size(
    wins: int,
    trials: int,
    payoff_b: float,
    available_budget: float,
    max_fraction: float = MAX_KELLY_FRACTION,
    min_samples: int = MIN_SAMPLES_FOR_CALIBRATION,
) -> Position:
    """带三重安全阀的仓位建议。

    ``payoff_b`` 例：一个商机测试花 1 万，成功后预期净赚 3 万，则 b = 3。
    """
    if available_budget < 0:
        raise ValueError("预算不能为负")
    if not 0.0 < max_fraction <= 1.0:
        raise ValueError("max_fraction 必须在 (0,1] 之间")

    # --- 安全阀 3：样本不足直接拒绝 ---
    if trials < min_samples:
        return Position(
            fraction=None, amount=None,
            win_rate_point=(wins / trials if trials else None),
            win_rate_lower=None, raw_kelly=None, n_samples=trials, refused=True,
            reason="calibration_not_established",
            explanation=(
                f"拒绝输出仓位：已解析结局 {trials} 条 < 所需 {min_samples} 条。",
                "Kelly 对胜率估计误差极度敏感 —— 用未校准的胜率下注，",
                "系统性高估会导致长期资本归零。此时应等额小注试探，",
                "由人决定金额，而不是让公式给一个看起来精确的数字。",
            ),
        )

    # --- 安全阀 1：用 Wilson 下界，不用点估计 ---
    p_point = wins / trials
    p_lower = wilson_lower_bound(wins, trials)
    raw = raw_kelly_fraction(p_lower, payoff_b)

    if raw <= 0:
        return Position(
            fraction=0.0, amount=0.0, win_rate_point=p_point,
            win_rate_lower=p_lower, raw_kelly=raw, n_samples=trials, refused=False,
            reason="negative_edge",
            explanation=(
                f"胜率下界 {p_lower:.1%}（点估计 {p_point:.1%}，n={trials}）",
                f"Kelly f* = ({payoff_b:g}×{p_lower:.4f} − {1-p_lower:.4f})"
                f" / {payoff_b:g} = {raw:.4f} ≤ 0",
                "负期望 —— 不下注。",
            ),
        )

    # --- 安全阀 2：¼ Kelly 硬上限 ---
    capped = min(raw * max_fraction, max_fraction)
    amount = capped * available_budget

    return Position(
        fraction=capped, amount=amount, win_rate_point=p_point,
        win_rate_lower=p_lower, raw_kelly=raw, n_samples=trials, refused=False,
        reason="ok",
        explanation=(
            f"胜率点估计 {p_point:.1%}，Wilson 下界 {p_lower:.1%}（n={trials}）",
            f"全 Kelly f* = ({payoff_b:g}×{p_lower:.4f} − {1-p_lower:.4f})"
            f" / {payoff_b:g} = {raw:.4f}",
            f"分数 Kelly（×{max_fraction:g}，上限 {max_fraction:g}）= {capped:.4f}",
            f"建议投入 = {capped:.4f} × {available_budget:,.0f} = {amount:,.0f} 元",
            "注：用胜率下界而非点估计，宁可少下注 —— 这是刻意的保守。",
        ),
    )


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------


def _selftest() -> int:
    failures = 0

    def check(label: str, ok: bool) -> None:
        nonlocal failures
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"  [{status}] {label}")

    print("oic.scoring.kelly 自检")

    p = position_size(wins=5, trials=10, payoff_b=3.0, available_budget=100_000)
    check("样本不足(n=10)时拒绝输出仓位", p.refused and p.fraction is None)

    p = position_size(wins=15, trials=30, payoff_b=3.0, available_budget=100_000)
    check("样本达标(n=30)时给出仓位", not p.refused and p.fraction is not None)
    check("仓位不超过 ¼ Kelly 上限", p.fraction is not None and p.fraction <= MAX_KELLY_FRACTION)

    lower = wilson_lower_bound(15, 30)
    check("Wilson 下界严格小于点估计", lower < 15 / 30)

    p_low = position_size(wins=1, trials=40, payoff_b=1.0, available_budget=100_000)
    check("负期望时仓位为 0", p_low.fraction == 0.0 and p_low.reason == "negative_edge")

    # 同样胜率下，样本越少下界越低 → 仓位越保守
    small = position_size(wins=20, trials=40, payoff_b=3.0, available_budget=100_000)
    large = position_size(wins=200, trials=400, payoff_b=3.0, available_budget=100_000)
    check("样本越少仓位越保守", small.fraction is not None and large.fraction is not None
          and small.fraction < large.fraction)

    print(f"\n{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
