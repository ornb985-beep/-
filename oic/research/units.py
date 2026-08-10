"""单位与币种归一。

原则：
  * 同币种内做量纲归一（万/亿/万亿 → 基本单位），这是无损的。
  * **跨币种转换有损**，因为汇率逐年变动。转换后必须打 ``converted=True``
    标记并记录所用汇率，让下游能降权或排除 —— 不许静默转换。
  * 数字脱离**年份**没有意义。本模块所有量都强制携带年份。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 量纲
# ---------------------------------------------------------------------------

#: 中文数量级词 → 倍数。按字符长度降序匹配，避免"万亿"被"万"截断。
SCALE_WORDS: tuple[tuple[str, float], ...] = (
    ("万亿", 1e12),
    ("千亿", 1e11),
    ("百亿", 1e10),
    ("亿", 1e8),
    ("千万", 1e7),
    ("百万", 1e6),
    ("万", 1e4),
    ("千", 1e3),
)

#: 英文数量级
EN_SCALE_WORDS: tuple[tuple[str, float], ...] = (
    ("trillion", 1e12),
    ("billion", 1e9),
    ("million", 1e6),
    ("thousand", 1e3),
)


class Currency:
    CNY = "CNY"
    USD = "USD"
    NONE = "NONE"          # 计数类（家、人、店），无币种


#: 人民币兑美元年均汇率（近似值）。
#:
#: ⚠️ 这些是**近似的年均值**，用于把美元口径的数字拉到可比范围，
#: 不是精确汇率。任何经此转换的数字都会被标记 converted=True，
#: 在双源锚定里按低一档可信度处理。
USD_CNY_ANNUAL_AVG: dict[int, float] = {
    2019: 6.90, 2020: 6.90, 2021: 6.45, 2022: 6.73,
    2023: 7.08, 2024: 7.20, 2025: 7.17, 2026: 7.15,
}


class UnitError(ValueError):
    pass


@dataclass(frozen=True)
class Quantity:
    """一个带年份、单位、币种的量。"""

    value: float               # 已归一到基本单位（元 / 个）
    currency: str              # Currency.*
    year: int
    raw_text: str = ""
    converted: bool = False    # 是否经过跨币种转换（有损）
    conversion_rate: float | None = None
    original_currency: str | None = None

    def __post_init__(self) -> None:
        if self.currency not in (Currency.CNY, Currency.USD, Currency.NONE):
            raise UnitError(f"未知币种: {self.currency}")
        if not 1900 <= self.year <= 2100:
            raise UnitError(f"年份不合理: {self.year}")

    def to_cny(self) -> "Quantity":
        """转成人民币。已是 CNY 或无币种则原样返回。"""
        if self.currency in (Currency.CNY, Currency.NONE):
            return self
        rate = USD_CNY_ANNUAL_AVG.get(self.year)
        if rate is None:
            raise UnitError(f"{self.year} 年无汇率数据 —— 拒绝猜测")
        return Quantity(
            value=self.value * rate,
            currency=Currency.CNY,
            year=self.year,
            raw_text=self.raw_text,
            converted=True,
            conversion_rate=rate,
            original_currency=self.currency,
        )

    def in_yi(self) -> float:
        """以「亿」为单位显示，方便人读。"""
        return self.value / 1e8

    def describe(self) -> str:
        base = f"{self.in_yi():.4g}亿{'元' if self.currency == Currency.CNY else ''}"
        if self.currency == Currency.NONE:
            base = f"{self.value:,.0f}"
        if self.converted:
            base += f"（由{self.original_currency}按{self.conversion_rate:g}折算，有损）"
        return f"{base} @{self.year}"


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------

_NUM = r"(\d+(?:\.\d+)?)"

_CNY_MARKERS = ("元", "人民币", "RMB", "¥")
_USD_MARKERS = ("美元", "美金", "USD", "$", "dollar")


def _detect_currency(text: str) -> str:
    # 先查美元 —— "美元" 里不含 "元" 的独立形式，但 "亿美元" 同时含 "元"，
    # 所以必须先判美元再判人民币，否则会误判。
    for marker in _USD_MARKERS:
        if marker in text:
            return Currency.USD
    for marker in _CNY_MARKERS:
        if marker in text:
            return Currency.CNY
    return Currency.NONE


def parse_quantity(text: str, year: int) -> Quantity:
    """从一段文本里解析出量。

        parse_quantity("市场规模 226.94 亿元", 2022)   → 2.2694e10 CNY
        parse_quantity("约 28.4 亿美元", 2024)         → 2.84e9 USD
        parse_quantity("超过 100 万家", 2022)          → 1e6 NONE

    找不到数字时抛错 —— **不返回 0**。
    """
    if not text or not text.strip():
        raise UnitError("文本为空")

    match = re.search(_NUM, text)
    if not match:
        raise UnitError(f"文本中没有数字: {text!r}")

    number = float(match.group(1))
    tail = text[match.end():]

    scale = 1.0
    for word, multiplier in SCALE_WORDS:
        if tail.lstrip().startswith(word):
            scale = multiplier
            break
    else:
        lowered = tail.lstrip().lower()
        for word, multiplier in EN_SCALE_WORDS:
            if lowered.startswith(word):
                scale = multiplier
                break

    return Quantity(
        value=number * scale,
        currency=_detect_currency(text),
        year=year,
        raw_text=text.strip(),
    )


def parse_percent(text: str) -> float:
    """解析增速百分数。'同比增长 27.3%' → 27.3；'下降 8.46%' → -8.46。"""
    if not text:
        raise UnitError("文本为空")
    match = re.search(_NUM + r"\s*%", text)
    if not match:
        raise UnitError(f"文本中没有百分数: {text!r}")
    value = float(match.group(1))
    head = text[:match.start()]
    if any(word in head for word in ("下降", "下滑", "减少", "回落", "降低", "跌", "负增长")):
        value = -value
    return value


def _selftest() -> int:
    failures = 0

    def check(label: str, ok: bool) -> None:
        nonlocal failures
        if not ok:
            failures += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    print("oic.research.units 自检\n")

    q = parse_quantity("市场规模 226.94 亿元", 2022)
    check("226.94亿元 → 2.2694e10", abs(q.value - 2.2694e10) < 1)
    check("识别为人民币", q.currency == Currency.CNY)

    u = parse_quantity("约 28.4 亿美元", 2024)
    check("28.4亿美元 识别为美元", u.currency == Currency.USD)
    check("亿美元不被误判为人民币", u.currency != Currency.CNY)

    c = u.to_cny()
    check("美元折算后标记 converted", c.converted is True)
    check("折算记录汇率", c.conversion_rate == 7.20)
    check("28.4亿美元 @2024 ≈ 204.5亿元", abs(c.in_yi() - 204.48) < 1)

    n = parse_quantity("超过 100 万家", 2022)
    check("100万家 → 1e6", abs(n.value - 1e6) < 1)
    check("计数类无币种", n.currency == Currency.NONE)

    t = parse_quantity("规模将突破 1 万亿元", 2026)
    check("万亿不被截断为万", abs(t.value - 1e12) < 1)

    check("同比增长27.3% → 27.3", abs(parse_percent("同比增长 27.3%") - 27.3) < 1e-9)
    check("同比下降8.46% → -8.46", abs(parse_percent("同比下降 8.46%") + 8.46) < 1e-9)

    try:
        parse_quantity("没有数字", 2022)
        check("无数字时抛错而非返回0", False)
    except UnitError:
        check("无数字时抛错而非返回0", True)

    try:
        Quantity(1.0, Currency.USD, 1800).to_cny()
        check("无汇率年份抛错", False)
    except UnitError:
        check("无汇率年份抛错", True)

    print(f"\n{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
