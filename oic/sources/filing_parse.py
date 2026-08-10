"""招股书解析 —— 章节定位 + 字段抽取，每个数字强制过 grounding。

设计要点：**抽取结果必须能指回原文的字符区间**。
这不是可选的严谨，是我亲身踩过的坑：上一轮手工从检索摘要转录数字，
把「3.81万」记成 3,810,000，放大 100 倍，因为绕过了字符级校验。

所以这里的 API 只返回 ``GroundedFact``——它必带 (start, end)，
且构造时就验证过该区间的文本里真的有那个数。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import Iterable, Sequence

from oic.evidence.grounding import Claim, verify_claim
from oic.research import metrics as mx
from oic.research.units import Currency, parse_percent, parse_quantity

# ---------------------------------------------------------------------------
# 章节定位
# ---------------------------------------------------------------------------

#: 中文招股书里含竞争格局信息的章节标题
CN_SECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("competition", r"(?:行业竞争(?:格局|状况)|市场竞争(?:格局|状况)|竞争对手)"),
    ("industry", r"(?:行业(?:概况|基本情况)|所处行业(?:情况|概况)|市场规模)"),
    ("market_share", r"(?:市场(?:份额|占有率)|市占率)"),
    ("risk", r"(?:风险因素|重大事项提示)"),
)

#: 英文 S-1 / 10-K
US_SECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("competition", r"(?:^|\n)\s*(?:Item\s+\d+\.?\s*)?Competition\b"),
    ("industry", r"(?:^|\n)\s*(?:Industry\s+Overview|Our\s+Industry|Market\s+Opportunity)\b"),
    ("risk", r"(?:^|\n)\s*(?:Item\s+1A\.?\s*)?Risk\s+Factors\b"),
)


@dataclass(frozen=True)
class Section:
    name: str
    start: int
    end: int
    text: str


#: 标题行允许的编号前缀：一、 / （二） / 1. / 第六节 / Item 1A.
_HEADING_PREFIX = re.compile(
    r"^\s*(?:第[一二三四五六七八九十百]+[节章]|"
    r"[（(]?[一二三四五六七八九十]+[)）]?[、.]?|"
    r"[（(]?\d+[)）]?[、.]?|"
    r"Item\s+\d+[A-Z]?\.?)?\s*"
)

#: 标题行的长度上限。超过这个长度的一定是正文，不是标题。
MAX_HEADING_LENGTH = 40


def split_sections(document: str, language: str = "zh") -> tuple[Section, ...]:
    """按章节标题切分。相邻标题之间即为该章节正文。

    **标题必须是独占一行的短行**（可带 一、/（二）/Item 1A. 等编号）。

    为什么这条约束是必需的：早期实现把模式在正文任意位置的出现都当成边界，
    结果"市场规模""市场份额"这类正文词组被误判为标题，文档被切成碎片，
    "行业前五大企业合计市场份额"正好被拦腰截断，CR5 永远抽不出来。
    真实招股书的标题都是短行 + 编号，按这个判才对。

    找不到任何标题时返回空 —— **不把整篇当成一个章节**，
    那会让后续抽取在无关文字里乱找数字。
    """
    patterns = CN_SECTION_PATTERNS if language == "zh" else US_SECTION_PATTERNS

    hits: list[tuple[int, str]] = []
    offset = 0
    for line in document.splitlines(keepends=True):
        stripped = line.strip()
        if stripped and len(stripped) <= MAX_HEADING_LENGTH:
            body = _HEADING_PREFIX.sub("", stripped, count=1)
            for name, pattern in patterns:
                if re.match(pattern.lstrip("^"), body, re.IGNORECASE) or \
                        re.fullmatch(rf"{pattern.lstrip('^')}.{{0,12}}", body,
                                     re.IGNORECASE):
                    hits.append((offset, name))
                    break
        offset += len(line)

    if not hits:
        return ()

    sections: list[Section] = []
    for i, (start, name) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(document)
        sections.append(Section(name, start, end, document[start:end]))
    return tuple(sections)


# ---------------------------------------------------------------------------
# 字段抽取
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GroundedFact:
    """一个已通过字符级校验的事实。

    ``span`` 是相对**整篇文档**的偏移，可直接回查原文。
    """

    metric_family: str
    metric_scope: str
    metric_measure: str
    year: int | None
    value: float
    currency: str
    span_start: int
    span_end: int
    quoted: str
    section: str

    @property
    def metric_key(self) -> mx.MetricKey:
        return mx.MetricKey(self.metric_family, self.metric_scope, self.metric_measure)

    def line(self) -> str:
        year = f"@{self.year}" if self.year else ""
        return (f"{self.metric_key.label()}{year} = {self.value:g} "
                f"[{self.span_start}:{self.span_end}] 「{self.quoted}」")


_YEAR = re.compile(r"(19|20)\d{2}\s*年?")

#: 句子终止符 —— 抽取窗口绝不跨越它。
#:
#: 为什么重要：不夹断的话，"市场规模" 的窗口会跨过句号抓到下一句的
#: "3800家"，grounding 校验照样通过（数字确实在窗口里），
#: 但**指标与数字的对应关系是错的**。字符级校验保证数字存在，
#: 保证不了它属于这个指标 —— 边界必须由句法给。
#:
#: 注意：**单个换行不算句子边界**。招股书 PDF 转文本后满是排版折行，
#: 「市场规模为\n226.94亿元」是一句话被折成两行。把 \n 当终止符会在
#: 数字之前夹断窗口，导致真数据被丢弃。只有空行才是真正的段落边界。
_SENTENCE_END = re.compile(r"[。；;]|\n\s*\n")

#: 抽取规则：(口径, 触发词正则, 值的形态)
#: 长触发词在前 —— "前五大企业合计市场份额" 必须先于 "市场份额" 匹配。
_CN_RULES: tuple[tuple[mx.MetricKey, str, str], ...] = (
    (mx.MARKET_SHARE_CR5,
     r"(?:行业)?前(?:五|5|十|10)大(?:企业)?(?:合计)?市场(?:份额|占有率)", "percent"),
    (mx.MARKET_SHARE_SELF, r"(?:公司)?市场(?:份额|占有率)", "percent"),
    (mx.MARKET_SIZE_ALL, r"市场规模", "quantity"),
    (mx.COMPANY_STOCK,
     r"(?:同行业|同类|行业内)?(?:现有|存续)?企业(?:数量|家数)", "count"),
    (mx.DEMAND_GROWTH, r"(?:同比|年均复合)?增(?:长|速)率?", "percent"),
)


def _nearest_year(document: str, position: int, window: int = 120) -> int | None:
    """在触发词前后找年份。找不到返回 None —— **不猜**。"""
    left = max(position - window, 0)
    candidates = [
        int(m.group(0)[:4])
        for m in _YEAR.finditer(document[left:position + window])
    ]
    plausible = [y for y in candidates if 1990 <= y <= 2100]
    return plausible[-1] if plausible else None


def extract_facts(
    document: str, language: str = "zh", max_span: int = 60
) -> tuple[tuple[GroundedFact, ...], tuple[str, ...]]:
    """抽取并逐条做字符级校验。

    返回 ``(通过校验的事实, 被丢弃的原因)``。
    **对不上原文的一律丢弃，不修补、不近似。**
    """
    facts: list[GroundedFact] = []
    rejected: list[str] = []

    for section in split_sections(document, language):
        if section.name not in ("competition", "industry", "market_share"):
            continue

        claimed: list[tuple[int, int]] = []      # 已被更长触发词占用的区间

        for key, trigger, kind in _CN_RULES:
            for match in re.finditer(trigger, section.text):
                start = section.start + match.start()

                # 窗口在下一个句子终止符处夹断，绝不跨句
                tail = document[start:start + max_span]
                stop = _SENTENCE_END.search(tail, match.end() - match.start())
                end = start + (stop.end() if stop else len(tail))
                window = document[start:end]

                # 长触发词优先：若本次匹配落在已被占用的区间内，跳过。
                # 否则 "市场份额" 会把 "前五大企业合计市场份额" 再抓一遍。
                if any(a <= start < b for a, b in claimed):
                    continue

                try:
                    if kind == "percent":
                        value = parse_percent(window)
                        currency = Currency.NONE
                    elif kind == "count":
                        quantity = parse_quantity(window, 2000)
                        value, currency = quantity.value, Currency.NONE
                    else:
                        year_guess = _nearest_year(document, start) or 2000
                        quantity = parse_quantity(window, year_guess)
                        value, currency = quantity.value, quantity.currency
                except ValueError:
                    continue

                claim = Claim(
                    claim_id=f"{section.name}:{start}",
                    metric=key.label(), value=value, unit="",
                    span_start=start, span_end=end,
                    source_url="", snapshot_hash="",
                )
                result = verify_claim(claim, document)
                if not result.accepted:
                    rejected.append(f"{key.label()}@{start}: {result.reason}")
                    continue

                claimed.append((start, end))
                facts.append(GroundedFact(
                    metric_family=key.family, metric_scope=key.scope,
                    metric_measure=key.measure,
                    year=_nearest_year(document, start),
                    value=value, currency=currency,
                    span_start=start, span_end=end,
                    quoted=window.strip(), section=section.name,
                ))

    # 去重：同一 (口径, 年份, 值) 只保留首次出现
    seen: set[tuple] = set()
    unique: list[GroundedFact] = []
    for fact in facts:
        signature = (fact.metric_key.label(), fact.year, round(fact.value, 6))
        if signature not in seen:
            seen.add(signature)
            unique.append(fact)

    return tuple(unique), tuple(rejected)


# ---------------------------------------------------------------------------
# 离线自检
# ---------------------------------------------------------------------------

#: 仿招股书片段。结构照搬真实披露格式，数字为构造值。
FIXTURE_CN = """
第六节 业务与技术

一、公司所处行业基本情况

（一）行业概况

根据中国轻工业联合会统计，2022年我国户外露营装备行业市场规模为
226.94亿元，较上年增长52.0%。预计2025年市场规模将进一步扩大。

（二）行业竞争格局

目前行业内企业数量为3800家，市场集中度较低。2022年，公司市场份额
为3.2%，行业前五大企业合计市场份额为18.5%。

二、风险因素

行业竞争加剧的风险：若未来市场竞争持续加剧，公司毛利率可能下降。
"""


def _selftest() -> int:
    failures = 0

    def check(label: str, ok: bool) -> None:
        nonlocal failures
        if not ok:
            failures += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    print("oic.sources.filing_parse 离线自检\n")

    sections = split_sections(FIXTURE_CN, "zh")
    names = {s.name for s in sections}
    check("定位到行业竞争格局章节", "competition" in names)
    check("定位到行业概况章节", "industry" in names)

    facts, rejected = extract_facts(FIXTURE_CN, "zh")
    print(f"\n  抽出 {len(facts)} 条已校验事实，丢弃 {len(rejected)} 条：")
    for fact in facts:
        print(f"    {fact.line()}")

    check("抽出至少 3 条事实", len(facts) >= 3)
    check("每条都带字符区间",
          all(f.span_end > f.span_start for f in facts))
    check("每条的原文片段真的含该数字",
          all(str(int(f.value)) in f.quoted.replace(",", "")
              or f"{f.value:g}" in f.quoted
              or f"{f.value/1e8:g}" in f.quoted
              for f in facts))

    cr5 = [f for f in facts if f.metric_key == mx.MARKET_SHARE_CR5]
    check("抽到 CR5 且口径正确", bool(cr5) and abs(cr5[0].value - 18.5) < 1e-9)

    own = [f for f in facts if f.metric_key == mx.MARKET_SHARE_SELF]
    check("自身份额 3.2% 与 CR5 分开存放",
          bool(own) and abs(own[0].value - 3.2) < 1e-9)

    check("份额不再被误标为 market_size",
          not any(f.metric_family == mx.Family.MARKET_SIZE
                  and f.value in (3.2, 18.5) for f in facts))

    sizes = [f for f in facts if f.metric_family == mx.Family.MARKET_SIZE]
    check("市场规模只抽到真正的规模值（226.94亿），未跨句抓到 3800",
          len(sizes) == 1 and abs(sizes[0].value - 2.2694e10) < 1)

    companies = [f for f in facts if f.metric_family == mx.Family.COMPANY_COUNT]
    check("抽到同业企业数（剪刀差需要的供给侧数据）",
          bool(companies) and abs(companies[0].value - 3800) < 1e-9)

    check("每条 span 都不跨句",
          all(not re.search(r"[。；]", f.quoted[:-1]) for f in facts))

    # 幻觉必须被拦
    from oic.evidence.grounding import Claim as _Claim
    fake = _Claim("x", "market_size", 99999.0, "", 0, 50, "", "")
    check("原文没有的数字被丢弃", not verify_claim(fake, FIXTURE_CN).accepted)

    # 无章节标题时不得把整篇当一节
    check("无章节标题时返回空而非整篇",
          split_sections("这是一段没有任何章节标题的普通文字。", "zh") == ())

    print(f"\n{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--offline" in sys.argv or "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
