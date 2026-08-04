"""中美申报文件取数适配器。

**取数与解析分离**：适配器只负责"给我这份文件的文本"，
解析交给 ``filing_parse``。这样本环境（出网被阻断）也能完整测试解析逻辑，
换到有网络的环境只需注入一个真的 fetcher。

    fetcher(url) -> str

不在模块里硬编码 HTTP 客户端，是因为不同部署环境的网络栈不同
（代理、证书、限速），把它做成参数比做成依赖更耐用。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

from oic.compliance.provenance import Registry

Fetcher = Callable[[str], str]


class FetchError(RuntimeError):
    """取数失败。**不返回空字符串** —— 空文本会被下游当成"这份文件没数据"。"""


@dataclass(frozen=True)
class FilingRef:
    """一份申报文件的引用。"""

    market: str            # "US" | "CN"
    issuer: str            # 公司名
    form_type: str         # S-1 / 10-K / 招股说明书
    filed_on: str          # ISO 日期 —— 决定能否过 as-of 闸
    url: str
    source_key: str        # provenance 登记表里的 key

    def label(self) -> str:
        return f"[{self.market}] {self.issuer} {self.form_type} ({self.filed_on})"


# ---------------------------------------------------------------------------
# 美国 · SEC EDGAR
# ---------------------------------------------------------------------------

SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SEC_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"

#: SEC 要求所有自动化请求带可识别的 User-Agent（含联系邮箱），
#: 否则会被限流甚至封禁。这是 ToS 的明文要求，不是可选项。
SEC_USER_AGENT_NOTE = (
    "SEC 要求 User-Agent 形如 'CompanyName contact@example.com'，"
    "且建议 ≤10 请求/秒。注入 fetcher 时必须设置。"
)

#: 招股书里最有价值的表单类型
US_FORMS_OF_INTEREST = ("S-1", "S-1/A", "424B4", "10-K", "20-F")


def edgar_submissions_url(cik: int) -> str:
    if cik <= 0:
        raise ValueError("CIK 必须为正整数")
    return SEC_SUBMISSIONS.format(cik=cik)


def parse_edgar_submissions(payload: dict, forms: Sequence[str] = US_FORMS_OF_INTEREST
                            ) -> tuple[FilingRef, ...]:
    """从 data.sec.gov 的 submissions JSON 里挑出感兴趣的申报。

    JSON 结构是列式的（filings.recent.form 与 .filingDate 等长并列），
    因此按下标对齐取值。
    """
    issuer = payload.get("name", "")
    cik = payload.get("cik")
    recent = (payload.get("filings") or {}).get("recent") or {}

    form_list = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accessions = recent.get("accessionNumber") or []
    documents = recent.get("primaryDocument") or []

    lengths = {len(form_list), len(dates), len(accessions), len(documents)}
    if len(lengths) > 1:
        raise ValueError(f"EDGAR 列式字段长度不一致: {sorted(lengths)} —— 结构可能已变更")

    wanted = set(forms)
    out: list[FilingRef] = []
    for i, form in enumerate(form_list):
        if form not in wanted:
            continue
        accession = accessions[i].replace("-", "")
        out.append(FilingRef(
            market="US", issuer=issuer, form_type=form, filed_on=dates[i],
            url=SEC_ARCHIVE.format(cik=cik, accession=accession, doc=documents[i]),
            source_key="sec_edgar",
        ))
    return tuple(out)


# ---------------------------------------------------------------------------
# 中国 · 巨潮资讯
# ---------------------------------------------------------------------------

CNINFO_SEARCH = "http://www.cninfo.com.cn/new/hisAnnouncement/query"

#: 巨潮公告分类里，招股说明书相关的关键词
CN_FORMS_OF_INTEREST = ("招股说明书", "招股意向书", "上市公告书", "年度报告")


def parse_cninfo_announcements(payload: dict) -> tuple[FilingRef, ...]:
    """从巨潮查询结果里挑出招股书类公告。"""
    records = payload.get("announcements") or []
    out: list[FilingRef] = []
    for record in records:
        title = record.get("announcementTitle", "")
        if not any(keyword in title for keyword in CN_FORMS_OF_INTEREST):
            continue
        # 巨潮的时间戳是毫秒
        stamp = record.get("announcementTime")
        filed_on = ""
        if isinstance(stamp, (int, float)):
            from datetime import datetime, timezone
            filed_on = datetime.fromtimestamp(
                stamp / 1000.0, tz=timezone.utc
            ).date().isoformat()
        out.append(FilingRef(
            market="CN",
            issuer=record.get("secName", ""),
            form_type=title,
            filed_on=filed_on,
            url="http://static.cninfo.com.cn/" + record.get("adjunctUrl", ""),
            source_key="cninfo",
        ))
    return tuple(out)


# ---------------------------------------------------------------------------
# 合规闸
# ---------------------------------------------------------------------------


def fetch_filing(ref: FilingRef, fetcher: Fetcher, registry: Registry) -> str:
    """取一份申报文件的正文。**先过数据源白名单**。

    招股书是法定公开披露，登记为 PUBLIC_DOWNLOAD，不是爬取。
    但它仍然必须先在 provenance 里放行 —— 没有例外通道。
    """
    registry.assert_source_allowed(ref.source_key)
    try:
        text = fetcher(ref.url)
    except Exception as exc:                       # 取数失败必须显式
        raise FetchError(f"{ref.label()} 取数失败: {exc}") from exc
    if not text or not text.strip():
        raise FetchError(
            f"{ref.label()} 返回空内容 —— 拒绝当作「该文件无数据」，"
            "空文本会被下游误读为真实结论"
        )
    return text
