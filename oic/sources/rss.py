"""RSS / Atom 适配器 —— 纯标准库。

RSS 在合规上的位置显著优于页面抓取：**发布方主动提供订阅源**，
是「被邀请读取」而非「绕过技术措施」。所以 36氪/虎嗅/亿欧这类源
应当优先走 RSS 而不是抓页面。

解析用 ``xml.etree``（标准库），不引第三方。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Sequence

#: Atom 命名空间
_ATOM = "{http://www.w3.org/2005/Atom}"

#: 常见日期格式。RSS 用 RFC 822，Atom 用 ISO 8601。
_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

_RFC822 = re.compile(
    r"(?:\w{3},\s*)?(\d{1,2})\s+(\w{3})\s+(\d{4})"
)
_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


class FeedError(ValueError):
    """订阅源解析失败。**不返回空列表** —— 空会被下游误读为「今天没内容」。"""


@dataclass(frozen=True)
class FeedItem:
    title: str
    link: str
    published_at: str        # ISO 日期；解析不出为空串
    summary: str
    source_key: str

    @property
    def has_date(self) -> bool:
        return bool(self.published_at)


def _normalize_date(text: str) -> str:
    """把 RFC822 / ISO 日期统一成 YYYY-MM-DD。认不出返回空串，**不猜今天**。"""
    if not text:
        return ""
    iso = _ISO.search(text)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"
    rfc = _RFC822.search(text)
    if rfc:
        day, mon, year = rfc.group(1), rfc.group(2), rfc.group(3)
        month = _MONTHS.get(mon)
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"
    return ""


def _text(node, *paths: str) -> str:
    for path in paths:
        found = node.find(path)
        if found is not None:
            if found.text:
                return found.text.strip()
            # Atom 的 link 在属性里
            href = found.get("href")
            if href:
                return href.strip()
    return ""


def parse_feed(xml_text: str, source_key: str) -> tuple[FeedItem, ...]:
    """解析 RSS 2.0 或 Atom。两种格式自动识别。"""
    if not xml_text or not xml_text.strip():
        raise FeedError(f"{source_key}: 订阅源内容为空")

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise FeedError(f"{source_key}: XML 解析失败 — {exc}") from exc

    items: list[FeedItem] = []

    # RSS 2.0
    for node in root.iter("item"):
        items.append(FeedItem(
            title=_text(node, "title"),
            link=_text(node, "link"),
            published_at=_normalize_date(_text(node, "pubDate", "date")),
            summary=_text(node, "description"),
            source_key=source_key,
        ))

    # Atom
    for node in root.iter(f"{_ATOM}entry"):
        items.append(FeedItem(
            title=_text(node, f"{_ATOM}title"),
            link=_text(node, f"{_ATOM}link"),
            published_at=_normalize_date(
                _text(node, f"{_ATOM}published", f"{_ATOM}updated")),
            summary=_text(node, f"{_ATOM}summary", f"{_ATOM}content"),
            source_key=source_key,
        ))

    if not items:
        raise FeedError(
            f"{source_key}: 未解析出任何条目 —— "
            "拒绝返回空列表，那会被上层误读为「今天没有新内容」"
        )
    return tuple(items)


def filter_by_date(items: Sequence[FeedItem], as_of: str) -> tuple[FeedItem, ...]:
    """按 as-of 过滤。**无日期的条目一律排除** —— 回测中日期不明即不可用。"""
    from oic.research.asof import is_available_at

    return tuple(
        item for item in items
        if item.has_date and is_available_at(item.published_at, as_of)
    )
