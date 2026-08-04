"""as-of 时间闸 —— 回测有效性的唯一技术保障。

回测最容易犯、也最难自查的错误是**用了未来信息**。
一条 2025 年的文章说"露营 2022 年其实已经见顶"，读起来像 2022 年的事实，
其实带着 2025 年的后见之明。

所以：**发布日期晚于 as-of 的观测，一律不得进入评分。代码强制。**

这不是提醒，是抛错。``tests/test_research.py::test_as_of_gate_blocks_future_evidence``
会把一条 2025 年的观测喂进 2022 评分，断言必须失败。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence


class LookaheadError(PermissionError):
    """检测到未来信息泄漏。"""


def parse_iso_date(text: str) -> date:
    """解析 YYYY-MM-DD 或 YYYY-MM 或 YYYY。

    只给年份时按**年末**计（12-31）—— 保守方向：
    宁可把一条模糊日期判为"太晚不能用"，也不要放进未来信息。
    """
    parts = text.strip().split("-")
    try:
        if len(parts) == 1:
            return date(int(parts[0]), 12, 31)
        if len(parts) == 2:
            year, month = int(parts[0]), int(parts[1])
            if month == 12:
                return date(year, 12, 31)
            # 该月最后一天 = 下月一号的前一天，同样取保守方向
            first_of_next = date(year, month + 1, 1)
            return date.fromordinal(first_of_next.toordinal() - 1)
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError) as exc:
        raise ValueError(f"无法解析日期: {text!r}") from exc


@dataclass(frozen=True)
class Dated:
    """任何带发布日期的东西都可以过闸。"""

    published_at: str

    @property
    def published_date(self) -> date:
        return parse_iso_date(self.published_at)


def is_available_at(published_at: str, as_of: str) -> bool:
    return parse_iso_date(published_at) <= parse_iso_date(as_of)


def assert_no_lookahead(published_at: str, as_of: str, what: str = "观测") -> None:
    """硬闸。晚于 as-of 即抛错。"""
    if not is_available_at(published_at, as_of):
        raise LookaheadError(
            f"未来信息泄漏：{what} 发布于 {published_at}，晚于 as-of {as_of}。\n"
            "回测中使用未来信息会让结果失去全部意义 —— 拒绝放行。"
        )


def filter_available(items: Iterable, as_of: str, attr: str = "published_at") -> list:
    """按 as-of 过滤，返回可用的那些。不抛错，用于统计覆盖率。"""
    out = []
    for item in items:
        published = getattr(item, attr, None) if not isinstance(item, dict) else item.get(attr)
        if published and is_available_at(published, as_of):
            out.append(item)
    return out


@dataclass(frozen=True)
class CoverageReport:
    total: int
    available: int
    excluded_future: int

    @property
    def coverage(self) -> float:
        return self.available / self.total if self.total else 0.0

    def line(self) -> str:
        return (f"as-of 可用 {self.available}/{self.total} 条"
                f"（{self.coverage:.0%}），因晚于截止日排除 {self.excluded_future} 条")


def coverage(items: Sequence, as_of: str, attr: str = "published_at") -> CoverageReport:
    available = filter_available(items, as_of, attr)
    return CoverageReport(len(items), len(available), len(items) - len(available))
