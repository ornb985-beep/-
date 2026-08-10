"""Span-grounding 硬校验 —— 本仓库里投入产出比最高的一段代码。

规则：LLM 抽出的每一条数值证据都必须附带 ``(start, end)`` 字符区间，
且该区间在原文中切出来的子串必须**真的包含那个数字**。
对不上就丢弃整条证据，不做修补、不做近似匹配。

为什么这么硬：数值幻觉是本系统最危险的错误类型 —— 一个编造的
"月销 3 万单"会一路传导到变现系数、TAM、排序分、仓位建议。
而字符级比对的成本是零，且不可能被提示词工程绕过。

一年可能丢掉一些本来正确的证据。这是刻意的取舍：
**宁可少一条证据，不可多一个幻觉数字。**
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Sequence

#: 中文数量单位 —— 抽取值可能写成"3万"而原文写"30000"，反之亦然
_UNIT_MULTIPLIERS: tuple[tuple[str, float], ...] = (
    ("亿", 1e8),
    ("万", 1e4),
    ("千", 1e3),
    ("百", 1e2),
)

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


class RejectReason:
    OK = "ok"
    SPAN_OUT_OF_RANGE = "span_out_of_range"
    SPAN_EMPTY = "span_empty"
    VALUE_NOT_IN_SPAN = "value_not_in_span"
    NO_NUMBER_IN_SPAN = "no_number_in_span"
    SNAPSHOT_MISMATCH = "snapshot_mismatch"


@dataclass(frozen=True)
class Claim:
    """一条待校验的数值证据。"""

    claim_id: str
    metric: str              # 如 "月销量"
    value: float             # LLM 抽出的数值
    unit: str                # 如 "单"
    span_start: int
    span_end: int
    source_url: str
    snapshot_hash: str


@dataclass(frozen=True)
class GroundingResult:
    claim: Claim
    accepted: bool
    reason: str
    matched_text: str
    quoted_span: str
    message: str


def normalize(text: str) -> str:
    """NFKC 归一 —— 消除全角/半角数字差异，但不改变字符计数语义。

    注意：NFKC 可能改变长度（如 ﬁ→fi），因此**只用于比对，不用于定位**。
    span 永远针对原始文本。
    """
    return unicodedata.normalize("NFKC", text)


def expand_numbers(text: str) -> tuple[float, ...]:
    """把文本里的数字连同中文单位展开成候选数值集合。

    "3万单" → (3.0, 30000.0)；"30000单" → (30000.0)。
    这样 LLM 写 30000 而原文写 3万 时仍能匹配上。
    """
    normalized = normalize(text)
    values: list[float] = []
    for match in _NUMBER_RE.finditer(normalized):
        raw = float(match.group(0))
        values.append(raw)
        tail = normalized[match.end():match.end() + 1]
        for unit, multiplier in _UNIT_MULTIPLIERS:
            if tail == unit:
                values.append(raw * multiplier)
    # 去重并排序，保证确定性
    return tuple(sorted(set(values)))


def _values_match(claimed: float, candidates: Sequence[float], rel_tol: float) -> float | None:
    """返回匹配上的候选值；无匹配返回 None。

    容差只覆盖浮点表示误差与"3万 vs 30000"这类等价写法，
    **不覆盖四舍五入**（原文 2.8 万不能匹配声称的 3 万）。
    """
    for candidate in candidates:
        if candidate == claimed:
            return candidate
        if claimed != 0.0 and abs(candidate - claimed) / abs(claimed) <= rel_tol:
            return candidate
    return None


def verify_claim(
    claim: Claim,
    raw_text: str,
    expected_snapshot_hash: str | None = None,
    rel_tol: float = 1e-9,
) -> GroundingResult:
    """校验单条证据。"""
    if expected_snapshot_hash is not None and claim.snapshot_hash != expected_snapshot_hash:
        return GroundingResult(
            claim, False, RejectReason.SNAPSHOT_MISMATCH, "", "",
            "快照哈希不匹配 —— 证据指向的原文已变化，丢弃",
        )

    if claim.span_start < 0 or claim.span_end > len(raw_text):
        return GroundingResult(
            claim, False, RejectReason.SPAN_OUT_OF_RANGE, "", "",
            f"span [{claim.span_start},{claim.span_end}) 越界（原文长度 {len(raw_text)}）—— 丢弃",
        )
    if claim.span_start >= claim.span_end:
        return GroundingResult(
            claim, False, RejectReason.SPAN_EMPTY, "", "",
            "span 为空 —— 丢弃",
        )

    quoted = raw_text[claim.span_start:claim.span_end]
    candidates = expand_numbers(quoted)

    if not candidates:
        return GroundingResult(
            claim, False, RejectReason.NO_NUMBER_IN_SPAN, "", quoted,
            f"span 内没有任何数字，却声称抽出了 {claim.value:g} —— 丢弃（疑似幻觉）",
        )

    matched = _values_match(claim.value, candidates, rel_tol)
    if matched is None:
        return GroundingResult(
            claim, False, RejectReason.VALUE_NOT_IN_SPAN, "", quoted,
            f"声称的 {claim.value:g} 不在 span 的数值集合 "
            f"{[f'{c:g}' for c in candidates]} 中 —— 丢弃（疑似幻觉或算错）",
        )

    return GroundingResult(
        claim, True, RejectReason.OK, f"{matched:g}", quoted,
        f"✅ {claim.metric} = {claim.value:g}{claim.unit} 已在原文字符级验证："
        f"「{quoted}」",
    )


@dataclass(frozen=True)
class BatchResult:
    accepted: tuple[GroundingResult, ...]
    rejected: tuple[GroundingResult, ...]

    @property
    def rejection_rate(self) -> float:
        total = len(self.accepted) + len(self.rejected)
        return len(self.rejected) / total if total else 0.0

    def summary(self) -> tuple[str, ...]:
        total = len(self.accepted) + len(self.rejected)
        lines = [f"证据校验：{len(self.accepted)}/{total} 条通过，"
                 f"丢弃率 {self.rejection_rate:.1%}"]
        if self.rejection_rate > 0.3:
            lines.append(
                "⚠️ 丢弃率 >30% —— 这不是数据问题，是抽取提示词或 schema 有问题。"
                "应改提示词，而不是放宽校验。"
            )
        lines.extend(r.message for r in self.rejected)
        return tuple(lines)


def verify_batch(
    claims: Iterable[Claim],
    raw_text: str,
    expected_snapshot_hash: str | None = None,
) -> BatchResult:
    accepted: list[GroundingResult] = []
    rejected: list[GroundingResult] = []
    for claim in claims:
        result = verify_claim(claim, raw_text, expected_snapshot_hash)
        (accepted if result.accepted else rejected).append(result)
    return BatchResult(tuple(accepted), tuple(rejected))


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

    print("oic.evidence.grounding 自检\n")

    raw = "据榜单显示，该单品近30天销量为 3万单，客单价 129 元，退货率 8.5%。"

    def make(value: float, start: int, end: int, metric: str = "月销量") -> Claim:
        return Claim("C1", metric, value, "单", start, end,
                     "https://example.com/x", "hash-abc")

    # 真实存在的数字（"3万单" 的位置）
    idx = raw.index("3万单")
    check("原文写「3万」、声称 30000 时通过",
          verify_claim(make(30000, idx, idx + 3), raw).accepted)
    check("原文写「3万」、声称 3 时也通过",
          verify_claim(make(3, idx, idx + 3), raw).accepted)

    # 幻觉数字
    result = verify_claim(make(50000, idx, idx + 3), raw)
    check("原文没有 50000 时丢弃", not result.accepted)
    check("丢弃理由为 value_not_in_span",
          result.reason == RejectReason.VALUE_NOT_IN_SPAN)

    # 四舍五入不放行
    raw2 = "月销 2.8 万单"
    i2 = raw2.index("2.8")
    check("2.8万 不能匹配声称的 3万",
          not verify_claim(make(30000, i2, i2 + 5), raw2).accepted)

    # span 内无数字
    j = raw.index("据榜单显示")
    check("span 内无数字时丢弃",
          verify_claim(make(30000, j, j + 5), raw).reason
          == RejectReason.NO_NUMBER_IN_SPAN)

    # span 越界
    check("span 越界时丢弃",
          verify_claim(make(30000, 0, len(raw) + 10), raw).reason
          == RejectReason.SPAN_OUT_OF_RANGE)
    check("span 为空时丢弃",
          verify_claim(make(30000, 5, 5), raw).reason == RejectReason.SPAN_EMPTY)

    # 快照变化
    stale = Claim("C9", "月销量", 30000, "单", idx, idx + 3,
                  "https://example.com/x", "hash-OLD")
    check("快照哈希不符时丢弃",
          verify_claim(stale, raw, expected_snapshot_hash="hash-abc").reason
          == RejectReason.SNAPSHOT_MISMATCH)

    # 全角数字
    raw3 = "客单价 １２９ 元"
    i3 = raw3.index("１２９")
    check("全角数字经 NFKC 归一后可匹配",
          verify_claim(make(129, i3, i3 + 3, "客单价"), raw3).accepted)

    # 批量
    batch = verify_batch(
        [make(30000, idx, idx + 3), make(999999, idx, idx + 3)], raw
    )
    check("批量：1 通过 1 丢弃",
          len(batch.accepted) == 1 and len(batch.rejected) == 1)
    check("丢弃率 50%", abs(batch.rejection_rate - 0.5) < 1e-9)

    print(f"\n{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
