"""变化率时间序列引擎 —— 「变化率 > 绝对值」的落点。

按「实体×指标」指纹建立每日快照，算出：

    首次出现            → NEW
    有历史              → 环比变化率 %
    有两期以上变化率    → 加速 / 减速 / 反转 / 平稳（二阶）

## 一条重要的设计分界

**分类是事实，打分是判断。这两件事在本模块里是分开的。**

- ``classify()`` 只回答"它比上期涨了还是跌了、加速还是减速"——
  这是算术，不掺任何价值观。
- ``velocity_score()`` 才把"在涨的给高分"这条**判断**加进去，
  且全部系数标 PRIOR。

为什么要分开：本仓库的回测里，2022 年公开增速最高的两个品类
（露营 +52%、剧本杀 +45%）到 2025 全灭。**n=7、p=0.63，不显著**，
所以既不能据此反着打分，也不该假装"涨=好"已经被验证。

把事实和判断混在一个函数里，就没法在拿到更多数据后只改判断那一半。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


class Trend:
    """一阶：方向。"""

    NEW = "new"                  # 首次出现，无历史可比
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class Shape:
    """二阶：变化率本身在怎么变。"""

    UNKNOWN = "unknown"          # 不足两期变化率
    ACCELERATING = "accelerating"  # 同向且更快
    DECELERATING = "decelerating"  # 同向但更慢
    REVERSING = "reversing"        # 方向翻转
    STEADY = "steady"              # 变化率基本不变


#: 变化率绝对值低于此值视为「平」，避免把噪声读成趋势。PRIOR。
FLAT_THRESHOLD_PCT = 2.0

#: 两期变化率之差低于此值视为「稳」。PRIOR。
STEADY_THRESHOLD_PCT = 5.0


@dataclass(frozen=True)
class Snapshot:
    """某指纹在某日的取值。日期由调用方传入 —— 本模块不读时钟。"""

    fingerprint: str
    date: str            # ISO
    value: float


@dataclass(frozen=True)
class VelocityReading:
    fingerprint: str
    n_points: int
    latest_value: float
    change_pct: float | None       # 最近一期环比 %
    prior_change_pct: float | None  # 上一期环比 %
    trend: str
    shape: str
    explanation: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_new(self) -> bool:
        return self.trend == Trend.NEW

    @property
    def has_second_order(self) -> bool:
        return self.shape != Shape.UNKNOWN


def _pct_change(now: float, before: float) -> float | None:
    """环比。基期为 0 时无定义 —— 返回 None，**不返回 0 也不除零**。"""
    if before == 0:
        return None
    return (now - before) / abs(before) * 100.0


def classify(
    snapshots: Sequence[Snapshot],
    flat_threshold: float = FLAT_THRESHOLD_PCT,
    steady_threshold: float = STEADY_THRESHOLD_PCT,
) -> VelocityReading:
    """纯算术分类。同一指纹的快照序列 → 一阶方向 + 二阶形态。

    同日多条取最后一条（后写覆盖），按日期升序处理。
    """
    if not snapshots:
        raise ValueError("快照序列为空 —— 应返回未知而非默认值")

    fingerprints = {s.fingerprint for s in snapshots}
    if len(fingerprints) != 1:
        raise ValueError(f"classify() 只接受同一指纹的序列，收到 {len(fingerprints)} 个")

    by_date: dict[str, float] = {}
    for snap in snapshots:
        by_date[snap.date] = snap.value
    dates = sorted(by_date)
    values = [by_date[d] for d in dates]

    fingerprint = snapshots[0].fingerprint
    latest = values[-1]
    n = len(values)

    if n == 1:
        return VelocityReading(
            fingerprint, 1, latest, None, None, Trend.NEW, Shape.UNKNOWN,
            (f"首次出现（{dates[0]}），值 {latest:g} —— 无历史可比，"
             "标「新出现」而非猜测趋势",),
        )

    change = _pct_change(values[-1], values[-2])
    prior = _pct_change(values[-2], values[-3]) if n >= 3 else None

    if change is None:
        return VelocityReading(
            fingerprint, n, latest, None, prior, Trend.FLAT, Shape.UNKNOWN,
            (f"上期值为 0，环比无定义 —— 拒绝输出变化率（{dates[-2]}→{dates[-1]}）",),
        )

    if abs(change) < flat_threshold:
        trend = Trend.FLAT
    elif change > 0:
        trend = Trend.UP
    else:
        trend = Trend.DOWN

    if prior is None:
        shape = Shape.UNKNOWN
    elif (change > 0) != (prior > 0) and abs(change) >= flat_threshold \
            and abs(prior) >= flat_threshold:
        shape = Shape.REVERSING
    elif abs(change - prior) < steady_threshold:
        shape = Shape.STEADY
    elif abs(change) > abs(prior):
        shape = Shape.ACCELERATING
    else:
        shape = Shape.DECELERATING

    lines = [
        f"{dates[-2]}→{dates[-1]}：{values[-2]:g} → {values[-1]:g}，"
        f"环比 {change:+.1f}%（{n} 期快照）",
    ]
    if prior is not None:
        labels = {
            Shape.ACCELERATING: "加速", Shape.DECELERATING: "减速",
            Shape.REVERSING: "反转", Shape.STEADY: "平稳", Shape.UNKNOWN: "未知",
        }
        lines.append(f"上期环比 {prior:+.1f}% → 本期 {change:+.1f}%，判定「{labels[shape]}」")
    else:
        lines.append("仅两期数据，二阶形态未知 —— 不猜")

    return VelocityReading(fingerprint, n, latest, change, prior, trend, shape,
                           tuple(lines))


# ---------------------------------------------------------------------------
# 打分（判断，与上面的事实分开）
# ---------------------------------------------------------------------------

#: 「只给在涨的高分」的系数表。**全部 PRIOR，未经真实结局验证。**
#:
#: 本仓库回测中，2022 年增速最高的品类到 2025 全灭（n=7, p=0.63, 不显著）。
#: 因此这张表既不能当作已验证，也不该反过来改成「越涨越扣分」——
#: 那同样是在噪声上拟合。改动它需要 ≥30 条真实结局。
#: 方向基准必须给幅度项与形态项留出余量：
#: 60（UP） + 20（幅度上限） + 20（加速） = 100 恰好用满。
#: 若基准给到 100，+20% 和 +100% 都会饱和成同一分，
#: 排序退化成按指纹字典序 —— 那等于没有排序。
TREND_WEIGHT: Mapping[str, float] = {
    Trend.UP: 0.6,
    Trend.FLAT: 0.4,
    Trend.DOWN: 0.2,
    Trend.NEW: 0.45,       # 新出现：可能是机会也可能是噪声，略低于「平」
}

SHAPE_BONUS: Mapping[str, float] = {
    Shape.ACCELERATING: 0.2,
    Shape.STEADY: 0.0,
    Shape.DECELERATING: -0.1,
    Shape.REVERSING: -0.2,
    Shape.UNKNOWN: 0.0,
}

#: 变化率饱和点：超过这个百分比不再加分。
#: 防止一条 +900% 的异常值压过所有正常信号。PRIOR。
CHANGE_SATURATION_PCT = 50.0


@dataclass(frozen=True)
class VelocityScore:
    fingerprint: str
    score: float           # 0–100
    reading: VelocityReading
    calibrated: bool
    explanation: tuple[str, ...]


def velocity_score(reading: VelocityReading) -> VelocityScore:
    """把分类结果折算成 0–100 分。

    **静态绝对值天然低分**：没有历史的信号只能拿到 NEW 档的中位分，
    因为"它有多大"不回答"它在不在涨"。
    """
    base = TREND_WEIGHT[reading.trend] * 100.0

    magnitude = 0.0
    if reading.change_pct is not None:
        capped = min(abs(reading.change_pct), CHANGE_SATURATION_PCT)
        magnitude = capped / CHANGE_SATURATION_PCT * 20.0
        if reading.change_pct < 0:
            magnitude = -magnitude

    bonus = SHAPE_BONUS[reading.shape] * 100.0
    score = max(0.0, min(base + magnitude + bonus, 100.0))

    lines = list(reading.explanation)
    lines.append(
        f"速度分 = 方向{base:.0f} + 幅度{magnitude:+.1f} + 形态{bonus:+.0f}"
        f" = {score:.1f}"
    )
    lines.append(
        "⚠️ 系数全部为 PRIOR，未经真实结局验证。"
        "回测中高增速品类反而失败（n=7, p=0.63, 不显著）—— "
        "既不能当已验证，也不该反向调整。"
    )
    return VelocityScore(reading.fingerprint, score, reading, False, tuple(lines))


# ---------------------------------------------------------------------------
# 序列存储
# ---------------------------------------------------------------------------


class SnapshotSeries:
    """按指纹分组的快照集合。纯内存，可序列化到 signal_series 表。"""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, float]] = {}

    def record(self, fingerprint: str, date: str, value: float) -> None:
        self._data.setdefault(fingerprint, {})[date] = value

    def record_many(self, snapshots: Iterable[Snapshot]) -> None:
        for snap in snapshots:
            self.record(snap.fingerprint, snap.date, snap.value)

    def snapshots(self, fingerprint: str) -> tuple[Snapshot, ...]:
        points = self._data.get(fingerprint, {})
        return tuple(Snapshot(fingerprint, d, points[d]) for d in sorted(points))

    def fingerprints(self) -> tuple[str, ...]:
        return tuple(sorted(self._data))

    def read(self, fingerprint: str) -> VelocityReading:
        snaps = self.snapshots(fingerprint)
        if not snaps:
            raise KeyError(f"指纹 {fingerprint} 无快照")
        return classify(snaps)

    def read_all(self) -> tuple[VelocityReading, ...]:
        return tuple(self.read(f) for f in self.fingerprints())

    def rank(self) -> tuple[VelocityScore, ...]:
        """按速度分排序。并列时用指纹作次级键，保证确定性。"""
        scored = [velocity_score(r) for r in self.read_all()]
        return tuple(sorted(scored, key=lambda s: (-s.score, s.fingerprint)))
