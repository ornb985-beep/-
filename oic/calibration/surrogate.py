"""代理结局的双通道闸门 —— 防 Goodhart。

想法：用 7 天留资率代替 90 天月销，把校准周期压到 1/6。
风险：优化 14 天留资率 ≠ 优化赚钱。免费领取的人不买，
系统会被训练成"优化领 free 的人"。这是 Goodhart 定律的教科书案例。

因此双通道，且分工不可互换：
    快通道（代理）→ 只用于**实验排序**，决定先验证哪 3 个
    慢通道（真值）→ 只有它能写入校准，决定系统是否有效

代理要升级为可信信号，必须先通过 Prentice 准则的可检验部分。
不通过就停用该代理，而不是"先用着"。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

#: 代理与真值的最小相关系数（PRIOR）
MIN_CORRELATION = 0.5
#: 代理需解释的处理效应比例下限（PRIOR）
MIN_PROPORTION_EXPLAINED = 0.5
#: 验证 Prentice 准则所需的最小配对样本
MIN_PAIRS_FOR_VALIDATION = 20


class Channel:
    """通道用途 —— 用常量而非布尔，避免调用点写反。"""

    RANKING_ONLY = "ranking_only"      # 快通道：只排序
    CALIBRATION = "calibration"        # 慢通道：可写入校准


@dataclass(frozen=True)
class SurrogateValidation:
    n_pairs: int
    correlation: float | None
    proportion_explained: float | None
    prentice_satisfied: bool
    allowed_channel: str
    reason: str
    explanation: tuple[str, ...]

    @property
    def may_write_calibration(self) -> bool:
        return self.allowed_channel == Channel.CALIBRATION


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """皮尔逊相关系数，纯标准库。"""
    n = len(xs)
    if n != len(ys):
        raise ValueError("两序列长度必须一致")
    if n < 2:
        raise ValueError("至少需要 2 个配对样本")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0.0 or syy == 0.0:
        raise ValueError("某一序列方差为 0 —— 相关系数无定义")
    return sxy / math.sqrt(sxx * syy)


def validate_surrogate(
    surrogate_values: Sequence[float],
    true_outcomes: Sequence[int],
    min_correlation: float = MIN_CORRELATION,
    min_proportion: float = MIN_PROPORTION_EXPLAINED,
    min_pairs: int = MIN_PAIRS_FOR_VALIDATION,
) -> SurrogateValidation:
    """检验代理是否够格升级到慢通道。

    这里只做 Prentice 准则里**可用观测数据检验**的部分：
      (a) 代理与真值相关；
      (b) 代理能解释足够比例的组间差异。

    Prentice 完整准则还要求"给定代理后，处理对真值无残余效应"，
    那需要随机化实验才能识别 —— 系统不做随机化，因此永远无法完全验证。
    **含义：代理最多降到"可信排序信号"，不该被当作真值的替代品。**
    """
    n = len(surrogate_values)
    if n != len(true_outcomes):
        raise ValueError("代理值与真实结局数量必须一致")

    if n < min_pairs:
        return SurrogateValidation(
            n_pairs=n, correlation=None, proportion_explained=None,
            prentice_satisfied=False, allowed_channel=Channel.RANKING_ONLY,
            reason="insufficient_pairs",
            explanation=(
                f"配对样本 {n} < {min_pairs} —— 无法检验代理有效性。",
                "代理限于快通道（仅用于实验排序），不得写入校准。",
            ),
        )

    try:
        r = pearson(surrogate_values, [float(o) for o in true_outcomes])
    except ValueError as exc:
        return SurrogateValidation(
            n_pairs=n, correlation=None, proportion_explained=None,
            prentice_satisfied=False, allowed_channel=Channel.RANKING_ONLY,
            reason="undefined_correlation",
            explanation=(f"相关系数无定义：{exc}", "代理限于快通道。"),
        )

    # 用 R² 作为"解释比例"的可观测代理
    proportion = r * r

    satisfied = r >= min_correlation and proportion >= min_proportion
    channel = Channel.CALIBRATION if satisfied else Channel.RANKING_ONLY

    lines = [
        f"配对样本 n = {n}",
        f"代理与真值相关 r = {r:.4f}（门槛 {min_correlation:g}）",
        f"解释比例 R² = {proportion:.4f}（门槛 {min_proportion:g}）",
    ]
    if satisfied:
        lines.extend([
            "✅ 可检验部分通过 —— 代理可参与校准。",
            "⚠️ 但 Prentice 的「无残余效应」条件需随机化实验才能识别，"
            "本系统不做随机化，因此代理始终只是可信信号，不是真值替代品。",
        ])
    else:
        lines.append(
            "❌ 未通过 —— 停用该代理写入校准。"
            "继续用它会把系统训练成优化代理本身（Goodhart）。"
        )

    return SurrogateValidation(
        n_pairs=n, correlation=r, proportion_explained=proportion,
        prentice_satisfied=satisfied, allowed_channel=channel,
        reason="ok" if satisfied else "failed_prentice",
        explanation=tuple(lines),
    )


def assert_channel(validation: SurrogateValidation, intended: str) -> None:
    """调用点保护：想把代理写进校准时，先过这道闸。"""
    if intended == Channel.CALIBRATION and not validation.may_write_calibration:
        raise PermissionError(
            "拒绝把代理结局写入校准：" + validation.reason + "。"
            "代理只能用于实验排序（快通道）。"
        )
