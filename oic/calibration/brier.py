"""Brier 分数与 Murphy 三分解。

    BS = (1/N) Σ(f_i − o_i)²        f=预测概率, o=结果(0/1)

    Murphy 三分解：
    BS = REL − RES + UNC
      UNC = ō(1−ō)   基础率基准 —— "啥都不做只报基础率"的分数
      REL = (1/N) Σ n_k(p_k − ō_k)²    校准误差，越小越好
      RES = (1/N) Σ n_k(ō_k − ō)²      区分力，越大越好

有用性硬判据：RES > REL（等价于 BS < UNC）。

小样本诚实原则：真实结果 <30 个时不得宣称"已校准"，
只报 Brier Skill Score 与 Root Brier Score（比分箱 ECE 稳健，
ECE 依赖分箱且箱数可人为操纵）。
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from typing import Sequence

from oic.config import MIN_SAMPLES_FOR_CALIBRATION

#: 默认分箱数（仅用于 Murphy 分解；报告首选 RBS 而非分箱 ECE）
DEFAULT_BINS = 10


def _validate(forecasts: Sequence[float], outcomes: Sequence[int]) -> None:
    if len(forecasts) != len(outcomes):
        raise ValueError("预测与结局数量必须一致")
    if not forecasts:
        raise ValueError("样本为空 —— 应返回未知而非 0")
    for f in forecasts:
        if not 0.0 <= f <= 1.0:
            raise ValueError(f"预测概率必须在 0–1 之间，收到 {f}")
    for o in outcomes:
        if o not in (0, 1):
            raise ValueError(f"结局必须是 0 或 1，收到 {o}")


def brier_score(forecasts: Sequence[float], outcomes: Sequence[int]) -> float:
    """BS = (1/N) Σ(f − o)²。范围 [0,1]，越低越好。

    直觉锚点：总用 80% 置信度且 80% 命中时 BS = 0.16 × ... 实际为
    0.8×0.04 + 0.2×0.64 = 0.16。GJP 锦标赛"中游"约在 0.3 量级。
    """
    _validate(forecasts, outcomes)
    return sum((f - o) ** 2 for f, o in zip(forecasts, outcomes)) / len(forecasts)


def root_brier_score(forecasts: Sequence[float], outcomes: Sequence[int]) -> float:
    """RBS = √BS。小样本下比分箱 ECE 稳健，是校准误差的上界。"""
    return math.sqrt(brier_score(forecasts, outcomes))


def base_rate(outcomes: Sequence[int]) -> float:
    """ō —— 观测到的基础率。"""
    if not outcomes:
        raise ValueError("样本为空")
    return sum(outcomes) / len(outcomes)


def uncertainty(outcomes: Sequence[int]) -> float:
    """UNC = ō(1−ō) —— "只报基础率"这个笨办法的得分。

    这是系统必须打败的基准线。打不过它，系统就没有存在价值。
    """
    o_bar = base_rate(outcomes)
    return o_bar * (1.0 - o_bar)


@dataclass(frozen=True)
class MurphyDecomposition:
    reliability: float      # REL 越小越好
    resolution: float       # RES 越大越好
    uncertainty: float      # UNC 基准
    binned_brier: float     # 分箱表示下的 BS，恒等式对它精确成立
    actual_brier: float     # 未分箱的真实 BS
    identity_residual: float  # binned_BS − (REL − RES + UNC)，应为浮点误差量级
    binning_loss: float     # actual_BS − binned_BS：分箱丢掉的箱内方差
    n_bins_used: int

    @property
    def is_useful(self) -> bool:
        """RES > REL ⟺ BS < UNC —— 系统比瞎猜基础率强。"""
        return self.resolution > self.reliability


def murphy_decomposition(
    forecasts: Sequence[float],
    outcomes: Sequence[int],
    n_bins: int = DEFAULT_BINS,
) -> MurphyDecomposition:
    """Murphy 三分解。

    恒等式 BS = REL − RES + UNC **只在"箱内预测取箱均值"的表示下精确成立**。
    连续预测在箱内还有方差，这部分被分箱丢掉了 —— 本函数把它作为
    ``binning_loss`` 如实单列，而不是藏进残差里假装恒等式成立。

    这也是为什么报告首选 RBS 而非分箱 ECE：分箱数可以人为操纵，
    箱越多 REL 越小，看起来越"校准"。
    """
    _validate(forecasts, outcomes)
    if n_bins < 1:
        raise ValueError("n_bins 必须为正")

    n = len(forecasts)
    o_bar = base_rate(outcomes)

    # 分箱：[0,1) 均分，1.0 归入最后一箱
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for f, o in zip(forecasts, outcomes):
        idx = min(int(f * n_bins), n_bins - 1)
        bins[idx].append((f, o))

    rel = 0.0
    res = 0.0
    used = 0
    for bucket in bins:
        if not bucket:
            continue
        used += 1
        n_k = len(bucket)
        p_k = sum(f for f, _ in bucket) / n_k     # 箱内平均预测
        o_k = sum(o for _, o in bucket) / n_k     # 箱内实际频率
        rel += n_k * (p_k - o_k) ** 2
        res += n_k * (o_k - o_bar) ** 2
    rel /= n
    res /= n

    unc = o_bar * (1.0 - o_bar)

    # 分箱表示下的 BS：每条预测用其所在箱的均值 p_k 代替。
    # 只有这样 BS = REL − RES + UNC 才是精确恒等式（可解析证明）。
    binned_bs = 0.0
    for bucket in bins:
        if not bucket:
            continue
        n_k = len(bucket)
        p_k = sum(f for f, _ in bucket) / n_k
        binned_bs += sum((p_k - o) ** 2 for _, o in bucket)
    binned_bs /= n

    actual_bs = sum((f - o) ** 2 for f, o in zip(forecasts, outcomes)) / n

    residual = binned_bs - (rel - res + unc)
    binning_loss = actual_bs - binned_bs

    return MurphyDecomposition(
        rel, res, unc, binned_bs, actual_bs, residual, binning_loss, used
    )


def brier_skill_score(
    forecasts: Sequence[float],
    outcomes: Sequence[int],
    baseline_forecasts: Sequence[float] | None = None,
) -> float:
    """BSS = 1 − BS_model / BS_baseline。

    >0 表示胜过基准；小样本下这是唯一有方向性意义的指标。
    ``baseline_forecasts`` 缺省时用"恒报基础率"作基准（即 BS_baseline = UNC）。
    """
    _validate(forecasts, outcomes)
    bs_model = brier_score(forecasts, outcomes)

    if baseline_forecasts is None:
        bs_base = uncertainty(outcomes)
    else:
        bs_base = brier_score(baseline_forecasts, outcomes)

    if bs_base == 0.0:
        raise ValueError(
            "基准 Brier 为 0 —— 结局全同（全 0 或全 1），"
            "此时 BSS 无定义。需要更多样本或更平衡的样本。"
        )
    return 1.0 - bs_model / bs_base


def calibration_status(n_resolved: int, minimum: int = MIN_SAMPLES_FOR_CALIBRATION) -> str:
    """界面必须显示的诚实标注。"""
    if n_resolved < minimum:
        return (f"校准未建立（已解析 {n_resolved}/{minimum} 条）—— "
                "仅报 BSS 与 RBS 的方向性结果，不得宣称已校准")
    return f"校准已建立（已解析 {n_resolved} 条）"


@dataclass(frozen=True)
class BrierReport:
    n: int
    brier: float
    root_brier: float
    base_rate: float
    skill_score: float | None
    decomposition: MurphyDecomposition | None
    status: str
    may_claim_effective: bool

    def lines(self) -> tuple[str, ...]:
        out = [
            f"样本数 N = {self.n}",
            f"基础率 ō = {self.base_rate:.4f}",
            f"Brier BS = {self.brier:.4f}",
            f"Root Brier RBS = {self.root_brier:.4f}",
        ]
        if self.skill_score is not None:
            verdict = "胜过基础率" if self.skill_score > 0 else "不如基础率"
            out.append(f"Brier Skill Score = {self.skill_score:+.4f} → {verdict}")
        if self.decomposition is not None:
            d = self.decomposition
            out.extend([
                f"Murphy 分解：REL={d.reliability:.4f}  RES={d.resolution:.4f}"
                f"  UNC={d.uncertainty:.4f}",
                f"恒等式校验 binnedBS − (REL−RES+UNC) = {d.identity_residual:.2e}",
                f"分箱损失（箱内方差，非误差）= {d.binning_loss:.4f}",
                f"有用性判据 RES > REL：{'✅ 通过' if d.is_useful else '❌ 未通过'}",
            ])
        out.append(self.status)
        if not self.may_claim_effective:
            out.append("⛔ 未达标 —— 不得对外宣称系统有效")
        return tuple(out)


def build_report(
    forecasts: Sequence[float],
    outcomes: Sequence[int],
    n_bins: int = DEFAULT_BINS,
    minimum: int = MIN_SAMPLES_FOR_CALIBRATION,
) -> BrierReport:
    """生成完整校准报告，并按样本量决定报哪些指标。"""
    _validate(forecasts, outcomes)
    n = len(forecasts)

    bs = brier_score(forecasts, outcomes)
    rbs = root_brier_score(forecasts, outcomes)
    o_bar = base_rate(outcomes)

    try:
        bss = brier_skill_score(forecasts, outcomes)
    except ValueError:
        bss = None

    # 小样本不做分箱分解 —— REL/ECE 方差极大，报出来是误导
    decomposition = murphy_decomposition(forecasts, outcomes, n_bins) if n >= minimum else None

    status = calibration_status(n, minimum)
    may_claim = decomposition is not None and decomposition.is_useful

    return BrierReport(n, bs, rbs, o_bar, bss, decomposition, status, may_claim)


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

    print("oic.calibration.brier 自检")

    # 已知答案对拍：完美预测
    check("完美预测 BS=0", brier_score([1.0, 0.0, 1.0], [1, 0, 1]) == 0.0)
    # 最差预测
    check("最差预测 BS=1", brier_score([0.0, 1.0], [1, 0]) == 1.0)
    # 手算：f=0.8 命中4次 / 未命中1次
    f = [0.8] * 5
    o = [1, 1, 1, 1, 0]
    expected = (4 * 0.04 + 1 * 0.64) / 5
    check(f"手算对拍 BS={expected:.4f}", abs(brier_score(f, o) - expected) < 1e-12)
    check("RBS = √BS", abs(root_brier_score(f, o) - math.sqrt(expected)) < 1e-12)

    # Murphy 恒等式
    forecasts = [i / 50.0 for i in range(50)]
    outcomes = [1 if (i * 7) % 10 < i / 5 else 0 for i in range(50)]
    d = murphy_decomposition(forecasts, outcomes)
    check(f"恒等式 binnedBS = REL−RES+UNC（残差 {d.identity_residual:.2e}）",
          abs(d.identity_residual) < 1e-9)
    check("分箱损失非负（箱内方差）", d.binning_loss >= -1e-12)
    check("分箱损失 = actualBS − binnedBS",
          abs((d.actual_brier - d.binned_brier) - d.binning_loss) < 1e-12)

    # 小样本必须拒绝分解
    report = build_report([0.6] * 10, [1, 0, 1, 1, 0, 1, 0, 1, 1, 0])
    check("样本<30 时不做 Murphy 分解", report.decomposition is None)
    check("样本<30 时不得宣称有效", report.may_claim_effective is False)
    check("样本<30 时状态标注为未建立", "校准未建立" in report.status)

    # 全同结局时 BSS 无定义，应报错而非返回默认值
    try:
        brier_skill_score([0.5, 0.5], [1, 1])
        check("结局全同时 BSS 抛错", False)
    except ValueError:
        check("结局全同时 BSS 抛错", True)

    # 有区分力的系统应通过判据
    good_f = [0.9] * 20 + [0.1] * 20
    good_o = [1] * 18 + [0] * 2 + [0] * 18 + [1] * 2
    good = build_report(good_f, good_o)
    check("高区分力系统通过 RES>REL 判据", good.may_claim_effective is True)

    # 无区分力（恒报基础率）不应通过
    flat = build_report([0.5] * 40, [1, 0] * 20)
    check("恒报基础率不通过判据", flat.may_claim_effective is False)

    print(f"\n{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
