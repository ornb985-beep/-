"""校准报告 CLI。

    python -m oic.calibration.report --selftest
    python -m oic.calibration.report --forecasts data/forecasts.jsonl

预测存档格式（每行一条 JSON）::

    {"opportunity_id": "...", "predicted_at": "2026-08-04",
     "base_rate": {"value": 0.12, "source": "同类目90天存活率"},
     "prediction": {"p10": 0.05, "p50": 0.23, "p90": 0.51},
     "category": "户外露营",
     "resolution_date": "2026-11-03", "actual_outcome": null}

``actual_outcome`` 为 null 的条目不参与校准 —— 未解析就是未解析，
不做任何插补。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from oic.calibration.brier import build_report
from oic.calibration.hierarchical import partial_pool
from oic.calibration.surrogate import Channel, assert_channel, validate_surrogate
from oic.config import DEFAULT_CONFIG


def load_forecasts(path: Path) -> tuple[list[float], list[int], list[str], int]:
    """读取预测存档，只返回已解析的条目。"""
    forecasts: list[float] = []
    outcomes: list[int] = []
    categories: list[str] = []
    unresolved = 0

    with path.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            actual = record.get("actual_outcome")
            if actual is None:
                unresolved += 1
                continue
            if actual not in (0, 1, True, False):
                raise ValueError(f"第 {lineno} 行 actual_outcome 非法: {actual!r}")
            p50 = record.get("prediction", {}).get("p50")
            if p50 is None:
                raise ValueError(f"第 {lineno} 行缺少 prediction.p50")
            forecasts.append(float(p50))
            outcomes.append(int(bool(actual)))
            categories.append(record.get("category", "unknown"))

    return forecasts, outcomes, categories, unresolved


def render(path: Path) -> int:
    forecasts, outcomes, categories, unresolved = load_forecasts(path)

    print(f"预测存档：{path}")
    print(f"未解析条目：{unresolved}（不参与校准，不做插补）\n")

    if not forecasts:
        print("已解析条目为 0 —— 校准未建立。")
        print("这不是错误：Outcome 表是整个系统的命门，今天不开始记，永远补不回来。")
        return 0

    report = build_report(forecasts, outcomes)
    for line in report.lines():
        print(" ", line)

    # 按品类做分层估计
    by_category: dict[str, tuple[int, int]] = {}
    for category, outcome in zip(categories, outcomes):
        k, n = by_category.get(category, (0, 0))
        by_category[category] = (k + outcome, n + 1)

    if by_category:
        print("\n分层校准（partial pooling）：")
        for category in sorted(by_category):
            estimate = partial_pool(
                by_category, category,
                fallback_global_rate=DEFAULT_CONFIG.track.base_rate_prior,
            )
            print(f"  [{category}] {estimate.pooled_rate:.1%} "
                  f"[{estimate.lower:.1%}, {estimate.upper:.1%}] "
                  f"n={estimate.n} 收缩={estimate.shrinkage:.2f}")

    return 0


def _selftest() -> int:
    failures = 0

    def check(label: str, ok: bool) -> None:
        nonlocal failures
        if not ok:
            failures += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    print("oic.calibration.report 自检")

    # --- Brier 库自检 ---
    from oic.calibration.brier import _selftest as brier_selftest
    print("\n[brier]")
    if brier_selftest() != 0:
        failures += 1

    # --- 分层 ---
    print("\n[hierarchical]")
    data = {"露营": (3, 5), "咖啡": (20, 100), "香氛": (0, 0)}
    camp = partial_pool(data, "露营")
    coffee = partial_pool(data, "咖啡")
    scent = partial_pool(data, "香氛")

    check("小样本品类收缩更强", camp.shrinkage > coffee.shrinkage)
    check("零样本品类完全借全局", abs(scent.pooled_rate - scent.global_rate) < 1e-9)
    check("零样本品类标记为借力", scent.borrowed is True)
    check("小样本区间比大样本宽",
          (camp.upper - camp.lower) > (coffee.upper - coffee.lower))
    check("收缩后估计落在原始率与全局率之间",
          camp.raw_rate is not None
          and min(camp.raw_rate, camp.global_rate) - 1e-9
          <= camp.pooled_rate
          <= max(camp.raw_rate, camp.global_rate) + 1e-9)

    # 全局无数据时必须拒绝
    try:
        partial_pool({}, "未知")
        check("全局无数据时抛错", False)
    except ValueError:
        check("全局无数据时抛错", True)

    # Beta 分位数正确性：Beta(1,1)=均匀分布
    from oic.calibration.hierarchical import beta_quantile, betainc
    check("Beta(1,1) 中位数 = 0.5", abs(beta_quantile(1, 1, 0.5) - 0.5) < 1e-6)
    check("Beta(1,1) CDF(0.3) = 0.3", abs(betainc(1, 1, 0.3) - 0.3) < 1e-9)
    check("Beta(2,2) 对称中位数 = 0.5", abs(beta_quantile(2, 2, 0.5) - 0.5) < 1e-6)

    # --- 代理双通道 ---
    print("\n[surrogate]")
    n = 40
    good_surrogate = [i / n for i in range(n)]
    aligned = [1 if i >= n // 2 else 0 for i in range(n)]
    good = validate_surrogate(good_surrogate, aligned)
    check("强相关代理可进校准通道", good.may_write_calibration is True)

    noisy = [1 if i % 2 == 0 else 0 for i in range(n)]
    bad = validate_surrogate(good_surrogate, noisy)
    check("弱相关代理被挡在快通道", bad.may_write_calibration is False)

    few = validate_surrogate([0.1, 0.2, 0.3], [0, 1, 1])
    check("样本不足时限于快通道", few.allowed_channel == Channel.RANKING_ONLY)

    try:
        assert_channel(bad, Channel.CALIBRATION)
        check("弱代理写校准时抛 PermissionError", False)
    except PermissionError:
        check("弱代理写校准时抛 PermissionError", True)

    assert_channel(bad, Channel.RANKING_ONLY)  # 排序用途应放行
    check("弱代理用于排序放行", True)

    print(f"\n{'=' * 40}\n{'全部通过' if failures == 0 else f'{failures} 组失败'}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    if "--forecasts" in argv:
        idx = argv.index("--forecasts")
        if idx + 1 >= len(argv):
            print("用法：--forecasts <path>", file=sys.stderr)
            return 2
        path = Path(argv[idx + 1])
        if not path.exists():
            print(f"文件不存在：{path}", file=sys.stderr)
            return 2
        return render(path)
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
