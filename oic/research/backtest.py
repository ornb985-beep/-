"""回测 —— 用真实历史数据回答"这套方法论到底有没有信号"。

协议见 ``data/research/PROTOCOL.md``。执行顺序不可颠倒：
冻结样本池 → 冻结结局定义 → 采 as-of 信号 → 评分 → 采结局 → 回填出报告。

本模块只做统计，不做判断。所有"信号强弱"的结论都由数字给出。

    python -m oic.research.backtest --dry-run    # 只查泄漏，不出结论
    python -m oic.research.backtest --report     # 完整报告
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from oic.research import metrics as mx
from oic.research.dossier import Observation, build_dossier, load_observations

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "research"
AS_OF = "2022-12-31"

#: 样本量低于此值时，任何相关系数都只能当方向性提示
MIN_N_FOR_STATISTICS = 8


# ---------------------------------------------------------------------------
# 纯标准库统计
# ---------------------------------------------------------------------------


def rank(values: list[float]) -> list[float]:
    """平均秩次（并列取平均），Spearman 需要。"""
    indexed = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and values[indexed[j + 1]] == values[indexed[i]]:
            j += 1
        average = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k]] = average
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman 秩相关。方差为 0 时抛错而非返回 0。"""
    if len(xs) != len(ys):
        raise ValueError("长度不一致")
    if len(xs) < 3:
        raise ValueError(f"样本 {len(xs)} < 3，秩相关无意义")
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx_ = sum(rx) / n
    my_ = sum(ry) / n
    sxy = sum((a - mx_) * (b - my_) for a, b in zip(rx, ry))
    sxx = sum((a - mx_) ** 2 for a in rx)
    syy = sum((b - my_) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        raise ValueError("某一序列全部并列 —— 秩相关无定义")
    return sxy / math.sqrt(sxx * syy)


def auc(scores: list[float], labels: list[int]) -> float:
    """AUC = 随机取一正一负，正样本分更高的概率。并列计 0.5。

    n 很小时 AUC 比 Brier 稳健得多，因为它只看排序不看标定。
    """
    pos = [s for s, l in zip(scores, labels) if l == 1]
    neg = [s for s, l in zip(scores, labels) if l == 0]
    if not pos or not neg:
        raise ValueError("正负样本必须都存在 —— AUC 无定义")
    wins = 0.0
    for p in pos:
        for q in neg:
            wins += 1.0 if p > q else (0.5 if p == q else 0.0)
    return wins / (len(pos) * len(neg))


# ---------------------------------------------------------------------------
# 品类信号
# ---------------------------------------------------------------------------


@dataclass
class CategorySignal:
    key: str
    name: str
    demand_growth: float | None = None      # 需求增速 %
    supply_growth: float | None = None      # 供给增速 %（企业注册/门店）
    funding_signal: float | None = None
    outcome_demand: int | None = None       # 主标签
    outcome_opportunity: int | None = None  # 副标签
    outcome_note: str = ""
    insufficient: tuple[str, ...] = field(default_factory=tuple)

    @property
    def scissors(self) -> float | None:
        """剪刀差 M = 需求增速 − 供给增速。任一缺失即 None，不外推。"""
        if self.demand_growth is None or self.supply_growth is None:
            return None
        return self.demand_growth - self.supply_growth

    @property
    def usable_for_q1(self) -> bool:
        return self.scissors is not None and self.outcome_demand is not None


def extract_signals(
    categories: list[dict], observations: list[Observation]
) -> list[CategorySignal]:
    """从档案里提取回测所需的信号。缺失即标记，不猜测。

    **审计结论会阻断下游使用**：某品类若被 ``audit`` 判为增速自洽性冲突
    （报告的增速与由两年数值推算的对不上），该品类的供给增速一律不采用。

    这一条是刻意的：咖啡 2021 新增 2.6 万家、2022 新增 1.9 万家（−26.9%），
    但来源说「同比增长 26.6%」。两者不可能同真，而我无法判定谁对。
    此时挑一个用，就是在挑对结论有利的那个。
    """
    from oic.research.audit import audit

    report = audit(observations)
    disputed_growth = {
        finding.category_key for finding in report.findings
        if finding.check == "growth_consistency"
    }

    signals: list[CategorySignal] = []

    for category in categories:
        key, name = category["key"], category["name"]
        dossier = build_dossier(key, name, observations, AS_OF, enforce_gate=True)

        signal = CategorySignal(key=key, name=name)
        missing: list[str] = []

        # 需求增速：优先直接观测到的增速，其次由两年存量推算
        demand = dossier.value(mx.DEMAND_GROWTH, 2022)
        if demand is None:
            demand = dossier.growth_pct(mx.MARKET_SIZE_ALL, 2022, 2021)
        if demand is None:
            missing.append("需求增速")
        signal.demand_growth = demand

        # 供给增速：优先直接观测到的企业注册同比，
        # 其次由两年新增注册数推算，最后退到门店数推算
        supply = dossier.value(
            mx.MetricKey(mx.Family.GROWTH_RATE, mx.Scope.DRIVEN, mx.Measure.FLOW), 2022
        )
        if supply is None:
            supply = dossier.growth_pct(mx.COMPANY_NEW, 2022, 2021)
        if supply is None:
            supply = dossier.growth_pct(
                mx.MetricKey(mx.Family.STORE_COUNT, mx.Scope.ALL, mx.Measure.STOCK),
                2022, 2020,
            )
            if supply is not None:
                supply /= 2.0     # 两年跨度折算成年化

        if key in disputed_growth:
            # 审计判定该品类的增速数据自相矛盾 —— 拒绝采用，不挑一个用
            supply = None
            missing.append("供给增速（来源冲突，审计已阻断）")
        elif supply is None:
            missing.append("供给增速")
        signal.supply_growth = supply

        signal.insufficient = tuple(missing)
        signals.append(signal)

    return signals


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------


def load_categories(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("//"):
                out.append(json.loads(line))
    return out


def load_outcomes(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("//"):
                record = json.loads(line)
                out[record["category_key"]] = record
    return out


def attach_outcomes(signals: list[CategorySignal], outcomes: dict[str, dict]) -> None:
    for signal in signals:
        record = outcomes.get(signal.key)
        if not record:
            continue
        signal.outcome_demand = record.get("outcome_demand")
        signal.outcome_opportunity = record.get("outcome_opportunity")
        signal.outcome_note = record.get("note", "")


def build_report(signals: list[CategorySignal]) -> list[str]:
    lines: list[str] = []
    add = lines.append

    total = len(signals)
    with_demand = [s for s in signals if s.demand_growth is not None]
    with_scissors = [s for s in signals if s.scissors is not None]
    with_outcome = [s for s in signals if s.outcome_demand is not None]

    add("## 覆盖率（按规则 E2，数据缺失的品类保留在分母里）")
    add("")
    add(f"- 样本池：{total} 个品类")
    add(f"- 有 as-of 2022 需求增速：{len(with_demand)}/{total}")
    add(f"- 有 as-of 2022 剪刀差（需求+供给都有）：{len(with_scissors)}/{total}")
    add(f"- 有 2025 结局：{len(with_outcome)}/{total}")
    add("")

    missing = [s for s in signals if s.insufficient]
    if missing:
        add("数据缺失明细：")
        for s in missing:
            add(f"  - {s.name}：缺 {'、'.join(s.insufficient)}")
        add("")

    add("## 逐品类信号（as-of 2022-12-31）")
    add("")
    add("| 品类 | 需求增速 | 供给增速 | 剪刀差 M | 主标签 | 副标签 |")
    add("|---|---:|---:|---:|:---:|:---:|")
    for s in sorted(signals, key=lambda x: (x.scissors is None, -(x.scissors or 0))):
        def fmt(v, suffix="%"):
            return "—" if v is None else f"{v:+.1f}{suffix}"
        def lab(v):
            return "—" if v is None else ("✅" if v == 1 else "❌")
        add(f"| {s.name} | {fmt(s.demand_growth)} | {fmt(s.supply_growth)} | "
            f"{fmt(s.scissors)} | {lab(s.outcome_demand)} | {lab(s.outcome_opportunity)} |")
    add("")

    # --- Q1 剪刀差有没有信号 ---
    add("## Q1 · 剪刀差有没有信号？")
    add("")
    q1 = [s for s in with_scissors if s.outcome_demand is not None]
    if len(q1) < 3:
        add(f"**无法回答。** 同时具备剪刀差与结局的品类只有 {len(q1)} 个，秩相关需要至少 3 个。")
        add("")
        add("这本身是结论：**供给侧数据的公开可得性远低于需求侧。**")
        add("剪刀差是本系统最大的差异化，但如果拿不到供给数据，它就无法计算——")
        add("这个工程问题必须先解决，否则整条差异化不成立。")
    else:
        try:
            rho = spearman([s.scissors for s in q1], [float(s.outcome_demand) for s in q1])
            add(f"- 样本 n = {len(q1)}")
            add(f"- Spearman ρ(剪刀差, 主标签) = **{rho:+.3f}**")
            verdict = "有方向性信号" if abs(rho) > 0.3 else "看不出信号"
            add(f"- 判据 |ρ| > 0.3：**{verdict}**")
        except ValueError as exc:
            add(f"**无法计算**：{exc}")
        try:
            a = auc([s.scissors for s in q1], [s.outcome_demand for s in q1])
            add(f"- AUC = **{a:.3f}**（0.5 = 等同抛硬币）")
        except ValueError as exc:
            add(f"- AUC 无法计算：{exc}")
        add("")
        if len(q1) < MIN_N_FOR_STATISTICS:
            add(f"⚠️ n={len(q1)} < {MIN_N_FOR_STATISTICS}，任何相关系数都只能当方向性提示，"
                "不构成统计证据。")
    add("")

    # --- Q1b 需求增速单独有没有信号（覆盖率更高）---
    add("## Q1b · 只看需求增速呢？")
    add("")
    q1b = [s for s in with_demand if s.outcome_demand is not None]
    if len(q1b) >= 3:
        xs = [s.demand_growth for s in q1b]
        ys = [s.outcome_demand for s in q1b]
        try:
            from oic.stats.overfit import expected_max_correlation
            from oic.stats.resample import bootstrap_ci, permutation_test_binary

            test = permutation_test_binary(xs, ys)
            add(f"- 样本 n = {len(q1b)}")
            add(f"- Spearman ρ(2022需求增速, 2025主标签) = **{test.statistic:+.3f}**")
            add(f"- **精确置换检验**：p = **{test.p_value:.3f}**"
                f"（穷举 {test.n_permutations} 种排列，非近似）")
            try:
                interval = bootstrap_ci(xs, ys, n_resamples=5000)
                add(f"- Bootstrap 90% 区间：[{interval.lower:+.3f}, {interval.upper:+.3f}]"
                    f" —— {'跨越 0' if interval.spans_zero else '不跨 0'}")
            except ValueError as exc:
                add(f"- Bootstrap 区间无法计算：{exc}")

            luck = expected_max_correlation(len(q1b), 1, n_simulations=3000)
            add(f"- **运气基线**：n={len(q1b)} 时纯随机的 |ρ| 中位数 "
                f"{luck.median_max_abs_rho:.3f}，95 分位 {luck.p95_max_abs_rho:.3f}")
            add("")
            if not luck.beats_luck(abs(test.statistic)):
                add(f"### 结论：**没有信号**")
                add("")
                add(f"观测 |ρ|={abs(test.statistic):.3f} 与纯随机的中位数 "
                    f"{luck.median_max_abs_rho:.3f} 基本相同，p={test.p_value:.2f}，"
                    "区间大幅跨零。")
                add("")
                add("**这不是「弱信号」，这就是噪声本身的样子。** "
                    "不要因为方向符合直觉就去解读它。")
            else:
                add("观测值超过运气基线，值得用更大样本继续查。")
            add("")
            add("**这一项的意义**：如果只看需求增速就能预测，那供给侧引擎"
                "（本系统最大差异化、也是最贵的数据）就没有增量价值。"
                "目前两者都没测出信号。")
        except ValueError as exc:
            add(f"无法计算：{exc}")
    else:
        add(f"样本不足（n={len(q1b)}）。")
    add("")

    # --- 多重检验警告 ---
    add("## ⚠️ 多重检验：为什么不能接着加特征")
    add("")
    try:
        from oic.stats.overfit import expected_max_correlation
        n_here = max(len(q1b), 3)
        add(f"| 试几个特征 | 运气的 \\|ρ\\| 中位数 | 95 分位 |")
        add("|---|---:|---:|")
        saturated = []
        for k in (1, 5, 20):
            luck = expected_max_correlation(n_here, k, n_simulations=1500)
            saturated.append(luck.p95_max_abs_rho)
            add(f"| {k} | {luck.median_max_abs_rho:.3f} | **{luck.p95_max_abs_rho:.3f}** |")
        add("")
        if max(saturated) - min(saturated) < 1e-9:
            add(f"**注意 95 分位三档相同**：n={n_here} 时二元标签只有有限种排列，"
                "相关系数取值离散且很粗，抽一次就常常撞到可能的最大值。")
            add("")
            add("**这本身就是结论 —— 样本小到任何相关系数都失去分辨力。**"
                "中位数一列仍能看出「试得越多、运气越好」的趋势。")
        else:
            add(f"在这个样本量下，试 20 个特征，纯运气就能刷出 "
                f"|ρ|≈{saturated[-1]:.2f}。")
        add("")
        add("所以「我们又测了剪刀差/切换势能/HHI/成熟度，发现 X 最相关」这类结论，")
        add("在 n 变大之前一律不成立 —— 这正是量化回测过拟合的经典陷阱。")
    except ValueError:
        pass
    add("")

    # --- Q3 排序有没有用 ---
    add("## Q3 · 排序有没有用？")
    add("")
    ranked = [s for s in with_demand if s.outcome_demand is not None]
    if len(ranked) >= 4:
        ordered = sorted(ranked, key=lambda s: -(s.demand_growth or 0))
        half = max(len(ordered) // 2, 1)
        top, bottom = ordered[:half], ordered[-half:]
        top_rate = sum(s.outcome_demand for s in top) / len(top)
        bottom_rate = sum(s.outcome_demand for s in bottom) / len(bottom)
        add(f"- 按 2022 需求增速排序，前 {len(top)} 名实际成功率 **{top_rate:.0%}**")
        add(f"- 后 {len(bottom)} 名实际成功率 **{bottom_rate:.0%}**")
        add(f"- 差值 **{top_rate - bottom_rate:+.0%}**（判据 > 0）")
    else:
        add(f"样本不足（n={len(ranked)}）。")
    add("")

    # --- 双标签打架 ---
    both = [s for s in signals
            if s.outcome_demand is not None and s.outcome_opportunity is not None]
    disagree = [s for s in both if s.outcome_demand != s.outcome_opportunity]
    add("## 双标签是否打架？")
    add("")
    if both:
        add(f"- 有双标签的品类：{len(both)} 个")
        add(f"- 两标签不一致：**{len(disagree)} 个**")
        for s in disagree:
            add(f"  - **{s.name}**：品类在涨但赚不到钱 —— {s.outcome_note}")
        if disagree:
            add("")
            add("**这是本轮最重要的发现之一。** 只用需求侧标签训练，"
                "系统会把人推进已经卷烂的赛道。")
    else:
        add("暂无双标签数据。")
    add("")

    return lines


def main(argv: list[str]) -> int:
    categories = load_categories(DATA_DIR / "categories.jsonl")
    observations = load_observations(DATA_DIR / "observations.jsonl")

    print(f"样本池 {len(categories)} 个品类，观测 {len(observations)} 条")

    try:
        signals = extract_signals(categories, observations)
    except PermissionError as exc:
        print(f"\n⛔ 未来信息泄漏，回测中止：\n{exc}", file=sys.stderr)
        return 1

    if "--dry-run" in argv:
        print("✅ as-of 时间闸检查通过，无未来信息泄漏")
        usable = sum(1 for s in signals if s.demand_growth is not None)
        print(f"   {usable}/{len(signals)} 个品类有可用的 as-of 需求信号")
        return 0

    outcomes = load_outcomes(DATA_DIR / "outcomes.jsonl")
    if not outcomes:
        print("\n⚠️ 结局数据尚未采集（data/research/outcomes.jsonl 不存在）。")
        print("   按协议，结局必须在 as-of 评分之后才采集。")
        return 0
    attach_outcomes(signals, outcomes)

    report = build_report(signals)
    text = "\n".join(report)
    print()
    print(text)

    if "--write" in argv:
        out = DATA_DIR / "backtest.report.md"
        header = ("# 回测报告\n\n"
                  f"as-of：{AS_OF} · 结局窗口：2025 · 样本池：{len(categories)} 个品类\n\n"
                  "> 回顾性回测，非实盘表现。协议见 PROTOCOL.md。\n\n")
        out.write_text(header + text + "\n", encoding="utf-8")
        print(f"\n已写入 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
