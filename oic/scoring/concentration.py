"""竞争格局 —— HHI 与集中度。

    HHI = Σ(市场份额_i)²      份额用百分数
    CRn = 前 n 家份额之和

判读：
    HHI < 1000        竞争充分/低集中
    1000 ≤ HHI ≤ 1800 中度集中
    HHI > 1800        高度集中
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

HHI_LOW = 1000.0
HHI_HIGH = 1800.0

#: 份额之和允许的浮点/统计误差
SHARE_SUM_TOLERANCE = 1.0


@dataclass(frozen=True)
class Concentration:
    hhi: float
    cr4: float
    cr5: float
    cr8: float
    band: str
    is_oligopoly: bool
    explanation: tuple[str, ...]


def hhi(shares_pct: Sequence[float]) -> float:
    """HHI = Σ(份额)²，份额以百分数计（如 25.0 表示 25%）。"""
    if not shares_pct:
        raise ValueError("份额列表为空 —— 应返回未知而非 0")
    if any(s < 0 for s in shares_pct):
        raise ValueError("份额不能为负")
    total = sum(shares_pct)
    if total > 100.0 + SHARE_SUM_TOLERANCE:
        raise ValueError(f"份额之和 {total:.2f}% 超过 100% —— 数据有误")
    return sum(s * s for s in shares_pct)


def concentration_ratio(shares_pct: Sequence[float], n: int) -> float:
    """CRn = 前 n 家份额之和。"""
    if n <= 0:
        raise ValueError("n 必须为正")
    return sum(sorted(shares_pct, reverse=True)[:n])


def analyze_concentration(shares_pct: Sequence[float]) -> Concentration:
    index = hhi(shares_pct)
    cr4 = concentration_ratio(shares_pct, 4)
    cr5 = concentration_ratio(shares_pct, 5)
    cr8 = concentration_ratio(shares_pct, 8)

    if index < HHI_LOW:
        band = "low"
    elif index <= HHI_HIGH:
        band = "moderate"
    else:
        band = "high"

    # CR4 ≥ 30% 或 CR8 ≥ 40% 视为寡占型
    oligopoly = cr4 >= 30.0 or cr8 >= 40.0

    labels = {"low": "竞争充分/低集中", "moderate": "中度集中", "high": "高度集中"}
    lines = [
        f"HHI = Σ(份额²) = {index:.1f} → {labels[band]}",
        f"CR4 = {cr4:.1f}%  CR5 = {cr5:.1f}%  CR8 = {cr8:.1f}%"
        f" → {'寡占型' if oligopoly else '竞争型'}市场",
    ]
    return Concentration(index, cr4, cr5, cr8, band, oligopoly, tuple(lines))
