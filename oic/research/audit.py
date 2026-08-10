"""纠错内核 —— 确定性检查，不用 LLM。

为什么不用 LLM 自查：我犯的那个 100× 单位错，正是 LLM 那一层引入的
（WebSearch 摘要把「万」译成 million）。让犯错者当裁判是无效的。
这里全部是可复现、可测试的算术与字符串检查。

六类检查，每一类都对应一个真实发生过的错误：

    ① 字符级回验    声称的数字必须真的出现在原文片段里
    ② 量级异常      同指标跨源差 >10× → 大概率是单位错，不是分歧
    ③ 存量/流量     新增注册 ≤ 存量（露营"新增330万 > 存量100万"）
    ④ 部分和 vs 整体 B端+C端 ≈ 整体
    ⑤ 增速自洽      报告增速 vs 两年存量推算的增速
    ⑥ 异常值隔离    偏离共识 >3×MAD 标记待人工复核

第 ①②③ 条都能独立抓住我犯的那个错。
"""

from __future__ import annotations

import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from oic.evidence.grounding import expand_numbers
from oic.research import metrics as mx
from oic.research.dossier import Observation, load_observations


class Severity:
    ERROR = "error"      # 数据几乎确定是错的，不修不能用
    WARN = "warn"        # 可疑，需人工看
    INFO = "info"


#: 同指标跨源差超过此倍数，判为单位错而非观点分歧
MAGNITUDE_RATIO_LIMIT = 10.0

#: 部分之和与整体的容差
PARTS_SUM_TOLERANCE = 0.15

#: 报告增速与推算增速的容差（百分点）
GROWTH_CONSISTENCY_TOLERANCE = 20.0

#: 稳健离群判据：偏离中位数超过 k 倍 MAD
MAD_MULTIPLIER = 3.0


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str
    category_key: str
    message: str
    observations: tuple[str, ...] = ()

    def line(self) -> str:
        mark = {"error": "🔴", "warn": "🟡", "info": "🔵"}[self.severity]
        return f"{mark} [{self.check}] {self.category_key}: {self.message}"


# ---------------------------------------------------------------------------
# ① 字符级回验
# ---------------------------------------------------------------------------


def check_grounding(observations: Sequence[Observation]) -> list[Finding]:
    """每条观测声称的数字，必须能在它自己的 snippet 里找到。

    这是唯一一条能抓住"手工转录时打错数量级"的检查 ——
    因为 snippet 存的是原文，而 value 是转录的结果。
    """
    findings: list[Finding] = []
    for obs in observations:
        if not obs.snippet.strip():
            findings.append(Finding(
                "grounding", Severity.WARN, obs.category_key,
                f"{obs.metric_key.label()}@{obs.year} 无原文片段，无法回验",
            ))
            continue

        candidates = expand_numbers(obs.snippet)
        if not candidates:
            findings.append(Finding(
                "grounding", Severity.ERROR, obs.category_key,
                f"{obs.metric_key.label()}@{obs.year} 声称 {obs.value:g}，"
                f"但原文片段里没有任何数字：「{obs.snippet[:40]}」",
            ))
            continue

        # 观测值已归一到基本单位，原文可能写成"3.81万"。
        # 因此同时接受：原值、原值/1e4、原值/1e8（人民币亿/万口径）。
        #
        # 增速类取绝对值比对：原文的符号由文字承载（"下滑70%"里只有 70），
        # 负号是 parse_percent 从"下滑/下降"推出来的，不会出现在数字里。
        magnitude = abs(obs.value) if obs.metric_family == mx.Family.GROWTH_RATE \
            else obs.value
        targets = {magnitude, magnitude / 1e4, magnitude / 1e8, magnitude * 1e4}
        matched = any(
            abs(c - t) <= max(abs(t) * 1e-6, 1e-9)
            for c in candidates for t in targets
        )
        if not matched:
            findings.append(Finding(
                "grounding", Severity.ERROR, obs.category_key,
                f"{obs.metric_key.label()}@{obs.year} 声称 {obs.value:g}，"
                f"但原文片段的数值集合 {[f'{c:g}' for c in candidates[:6]]} 对不上 ——"
                " 疑似转录错误或单位错",
                (obs.source_name,),
            ))
    return findings


# ---------------------------------------------------------------------------
# ② 量级异常
# ---------------------------------------------------------------------------


def check_magnitude(observations: Sequence[Observation]) -> list[Finding]:
    """同一 (品类, 口径, 年份) 下，最大值/最小值 >10× 判为单位错。

    真实的口径分歧很少差一个数量级；差 100× 几乎一定是「万/million」这类错。
    """
    findings: list[Finding] = []
    buckets: dict[tuple, list[Observation]] = defaultdict(list)
    for obs in observations:
        buckets[(obs.category_key, obs.metric_key.label(), obs.year)].append(obs)

    for (category, label, year), group in sorted(buckets.items()):
        values = [o.value for o in group if o.value > 0]
        if len(values) < 2:
            continue
        ratio = max(values) / min(values)
        if ratio > MAGNITUDE_RATIO_LIMIT:
            findings.append(Finding(
                "magnitude", Severity.ERROR, category,
                f"{label}@{year} 跨源相差 {ratio:.0f}× "
                f"（{min(values):g} vs {max(values):g}）—— 超过 {MAGNITUDE_RATIO_LIMIT:g}× "
                "几乎一定是单位错，不是观点分歧",
                tuple(o.source_name for o in group),
            ))
    return findings


# ---------------------------------------------------------------------------
# ③ 存量 / 流量一致性
# ---------------------------------------------------------------------------


def check_stock_flow(observations: Sequence[Observation]) -> list[Finding]:
    """新增注册数不可能大于存续企业数。

    露营那条「2022 新注册 330 万家」vs「存量超 100 万家」就是被这条抓住的。
    """
    findings: list[Finding] = []
    stock: dict[tuple[str, int], float] = {}
    flow: dict[tuple[str, int], float] = {}

    for obs in observations:
        if obs.metric_family != mx.Family.COMPANY_COUNT:
            continue
        key = (obs.category_key, obs.year)
        target = stock if obs.metric_measure == mx.Measure.STOCK else flow
        target[key] = max(target.get(key, 0.0), obs.value)

    for key, new_count in sorted(flow.items()):
        category, year = key
        # 同年存量，或最近的任一年存量
        existing = stock.get(key)
        if existing is None:
            same_category = [v for (c, _), v in stock.items() if c == category]
            existing = max(same_category) if same_category else None
        if existing is None:
            continue
        if new_count > existing:
            findings.append(Finding(
                "stock_flow", Severity.ERROR, category,
                f"{year} 年新增企业 {new_count:,.0f} 家 > 存续企业 {existing:,.0f} 家 ——"
                " 逻辑不可能。多半是把「万」当成了 million，或混淆了存量与流量",
            ))
    return findings


# ---------------------------------------------------------------------------
# ④ 部分之和 vs 整体
# ---------------------------------------------------------------------------

_PART_SCOPES = (mx.Scope.B2B, mx.Scope.B2C)


def check_parts_sum(observations: Sequence[Observation]) -> list[Finding]:
    """B端 + C端 应当约等于整体。差太多说明口径不兼容。"""
    findings: list[Finding] = []
    by_key: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    for obs in observations:
        if obs.metric_family != mx.Family.MARKET_SIZE:
            continue
        by_key[(obs.category_key, obs.year)][obs.metric_scope] = obs.value

    for (category, year), scopes in sorted(by_key.items()):
        whole = scopes.get(mx.Scope.ALL)
        parts = [scopes[s] for s in _PART_SCOPES if s in scopes]
        if whole is None or len(parts) < len(_PART_SCOPES):
            continue
        total = sum(parts)
        deviation = abs(total - whole) / whole if whole else 0.0
        if deviation > PARTS_SUM_TOLERANCE:
            findings.append(Finding(
                "parts_sum", Severity.WARN, category,
                f"{year} 年 B端+C端 = {total:,.0f} 与整体 {whole:,.0f} 差 "
                f"{deviation:.0%} —— 口径可能不兼容，不应混用",
            ))
    return findings


# ---------------------------------------------------------------------------
# ⑤ 增速自洽
# ---------------------------------------------------------------------------


def check_growth_consistency(observations: Sequence[Observation]) -> list[Finding]:
    """报告的增速 vs 由两年数值推算的增速。

    同时覆盖市场规模与企业数 —— 后者是真实踩到的坑：
    咖啡 2021 新增 2.6 万家、2022 新增 1.9 万家（−27%），
    但同一批来源说 2022「同比增长 26.6%」。两者不可能同真。
    """
    findings: list[Finding] = []
    series: dict[tuple[str, str, str, int], float] = {}
    reported: dict[tuple[str, str, int], float] = {}

    for obs in observations:
        if obs.metric_family in (mx.Family.MARKET_SIZE, mx.Family.COMPANY_COUNT):
            key = (obs.category_key, obs.metric_family, obs.metric_scope, obs.year)
            # 同年多源取中位数量级的那个，避免被离群值带偏
            series.setdefault(key, obs.value)
        elif obs.metric_family == mx.Family.GROWTH_RATE:
            reported[(obs.category_key, obs.metric_scope, obs.year)] = obs.value

    #: 增速口径 → 它应当对应的数值口径
    _PAIRING = (
        (mx.Scope.ALL, mx.Family.MARKET_SIZE, (mx.Scope.ALL, mx.Scope.CORE), "市场规模"),
        (mx.Scope.DRIVEN, mx.Family.COMPANY_COUNT, (mx.Scope.ALL,), "新增企业数"),
    )

    for (category, growth_scope, year), stated in sorted(reported.items()):
        for want_scope, family, value_scopes, label in _PAIRING:
            if growth_scope != want_scope:
                continue
            for scope in value_scopes:
                now = series.get((category, family, scope, year))
                before = series.get((category, family, scope, year - 1))
                if now is None or before is None or before == 0:
                    continue
                implied = (now - before) / before * 100.0
                if abs(implied - stated) > GROWTH_CONSISTENCY_TOLERANCE:
                    findings.append(Finding(
                        "growth_consistency", Severity.WARN, category,
                        f"{year} 年报告增速 {stated:+.1f}%，但由 {year-1}→{year} "
                        f"{label}推算为 {implied:+.1f}%，"
                        f"差 {abs(implied - stated):.1f} 个百分点 —— 两组数字不可能同真，"
                        "需人工判定采信哪一个",
                    ))
    return findings


# ---------------------------------------------------------------------------
# ⑥ 异常值隔离
# ---------------------------------------------------------------------------


def check_outliers(observations: Sequence[Observation]) -> list[Finding]:
    """稳健离群检测：偏离中位数 >3×MAD。用 MAD 而非标准差，避免被离群值本身带偏。"""
    findings: list[Finding] = []
    buckets: dict[tuple, list[Observation]] = defaultdict(list)
    for obs in observations:
        buckets[(obs.category_key, obs.metric_key.label(), obs.year)].append(obs)

    for (category, label, year), group in sorted(buckets.items()):
        if len(group) < 3:
            continue
        values = [o.value for o in group]
        median = statistics.median(values)
        deviations = [abs(v - median) for v in values]
        mad = statistics.median(deviations)
        if mad == 0:
            continue
        for obs in group:
            if abs(obs.value - median) > MAD_MULTIPLIER * mad:
                findings.append(Finding(
                    "outlier", Severity.WARN, category,
                    f"{label}@{year} 来源 {obs.source_name} 报 {obs.value:g}，"
                    f"偏离中位数 {median:g} 超过 {MAD_MULTIPLIER:g}×MAD —— 待人工复核",
                    (obs.source_name,),
                ))
    return findings


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------

ALL_CHECKS = (
    ("grounding", check_grounding),
    ("magnitude", check_magnitude),
    ("stock_flow", check_stock_flow),
    ("parts_sum", check_parts_sum),
    ("growth_consistency", check_growth_consistency),
    ("outlier", check_outliers),
)


@dataclass(frozen=True)
class AuditReport:
    findings: tuple[Finding, ...]
    n_observations: int

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == Severity.WARN)

    @property
    def clean(self) -> bool:
        return not self.errors

    def lines(self) -> tuple[str, ...]:
        out = [f"扫描 {self.n_observations} 条观测："
               f"{len(self.errors)} 个错误、{len(self.warnings)} 个警告"]
        out.extend(f.line() for f in self.findings)
        if self.clean and not self.warnings:
            out.append("✅ 全部通过")
        return tuple(out)


def audit(observations: Sequence[Observation]) -> AuditReport:
    findings: list[Finding] = []
    for _, check in ALL_CHECKS:
        findings.extend(check(observations))
    order = {Severity.ERROR: 0, Severity.WARN: 1, Severity.INFO: 2}
    findings.sort(key=lambda f: (order[f.severity], f.check, f.category_key))
    return AuditReport(tuple(findings), len(observations))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _obs(category, key, year, value, source, snippet, measure=None):
    return Observation(
        category_key=category, metric_family=key.family, metric_scope=key.scope,
        metric_measure=measure or key.measure, year=year, value=value,
        currency="NONE", unit_note="", source_url="https://example.com",
        source_name=source, source_grade="B", published_at="2022-06-01",
        retrieved_at="2026-08-04", snippet=snippet,
    )


def _selftest() -> int:
    failures = 0

    def check(label: str, ok: bool) -> None:
        nonlocal failures
        if not ok:
            failures += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    print("oic.research.audit 自检\n")
    print("能否抓住我自己犯的那个 100× 错误：")

    # 真实错误重现：原文是"3.81万家"，我转录成 3,810,000
    bad = _obs("camping", mx.COMPANY_NEW, 2022, 3_810_000.0, "cnfin",
               "2022年露营相关企业注册同比增50.02%，达3.81万家")
    report = audit([bad])
    check("① 字符级回验抓住转录错误",
          any(f.check == "grounding" and f.severity == Severity.ERROR
              for f in report.findings))

    good = _obs("camping", mx.COMPANY_NEW, 2022, 38_100.0, "cnfin",
                "2022年露营相关企业注册同比增50.02%，达3.81万家")
    check("① 修正后放行",
          not any(f.check == "grounding" and f.severity == Severity.ERROR
                  for f in audit([good]).findings))

    # ② 量级
    pair = [
        _obs("x", mx.MARKET_SIZE_ALL, 2022, 100.0, "a", "100"),
        _obs("x", mx.MARKET_SIZE_ALL, 2022, 10000.0, "b", "10000"),
    ]
    check("② 量级异常 100× 被抓",
          any(f.check == "magnitude" for f in audit(pair).findings))

    # ③ 存量/流量
    sf = [
        _obs("camping", mx.COMPANY_NEW, 2022, 3_300_000.0, "a", "330万家"),
        _obs("camping", mx.COMPANY_STOCK, 2022, 1_000_000.0, "b", "100万家"),
    ]
    check("③ 新增>存量被抓",
          any(f.check == "stock_flow" for f in audit(sf).findings))

    # ④ 部分和
    parts = [
        _obs("meal", mx.MetricKey(mx.Family.MARKET_SIZE, mx.Scope.B2B, mx.Measure.STOCK),
             2025, 4200.0, "a", "4200"),
        _obs("meal", mx.MetricKey(mx.Family.MARKET_SIZE, mx.Scope.B2C, mx.Measure.STOCK),
             2025, 1973.0, "b", "1973"),
        _obs("meal", mx.MARKET_SIZE_ALL, 2025, 6173.0, "c", "6173"),
    ]
    check("④ 预制菜 4200+1973=6173 自洽，不报警",
          not any(f.check == "parts_sum" for f in audit(parts).findings))

    bad_parts = parts[:2] + [_obs("meal", mx.MARKET_SIZE_ALL, 2025, 3000.0, "c", "3000")]
    check("④ 部分和与整体不符被抓",
          any(f.check == "parts_sum" for f in audit(bad_parts).findings))

    # ⑤ 增速自洽
    growth = [
        _obs("y", mx.MARKET_SIZE_ALL, 2021, 100.0, "a", "100"),
        _obs("y", mx.MARKET_SIZE_ALL, 2022, 110.0, "a", "110"),
        _obs("y", mx.DEMAND_GROWTH, 2022, 80.0, "b", "同比增长80%"),
    ]
    check("⑤ 报告增速80%与推算10%不符被抓",
          any(f.check == "growth_consistency" for f in audit(growth).findings))

    # ⑥ 离群
    outlier = [
        _obs("z", mx.MARKET_SIZE_ALL, 2022, 100.0, "a", "100"),
        _obs("z", mx.MARKET_SIZE_ALL, 2022, 102.0, "b", "102"),
        _obs("z", mx.MARKET_SIZE_ALL, 2022, 105.0, "c", "105"),
        _obs("z", mx.MARKET_SIZE_ALL, 2022, 900.0, "d", "900"),
    ]
    check("⑥ 离群源被标记",
          any(f.check == "outlier" for f in audit(outlier).findings))

    print(f"\n{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()

    path = Path(__file__).resolve().parents[2] / "data" / "research" / "observations.jsonl"
    observations = load_observations(path)
    report = audit(observations)
    for line in report.lines():
        print(line)
    if report.errors:
        print(f"\n⛔ {len(report.errors)} 个错误必须修复后才能用于评分")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
