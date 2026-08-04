"""数据源登记表 —— 未登记的源在代码层无法被调用。

为什么是白名单而不是文档约定：
德恒统计 2011–2022 的 12 起"爬虫+不正当竞争"案，**爬取方胜诉率
不到 16.67%**；2025 年《反不正当竞争法》新增数据专款第13条第3款
（不得以避开或破坏技术管理措施等方式获取他人合法持有的数据）。

一条写在文档里的"优先用官方 API"约束，在赶进度时会被绕过。
一条写在 ``assert_source_allowed`` 里的约束不会。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


class AccessMethod:
    OFFICIAL_API = "official_api"        # 官方开放 API
    LICENSED_PURCHASE = "licensed"       # 采购/授权数据交付
    PUBLIC_DOWNLOAD = "public_download"  # 官方公开下载（如商标网公告）
    USER_PROVIDED = "user_provided"      # 用户自行上传/授权
    SCRAPING = "scraping"                # 爬取 —— 默认不允许


class LegalStatus:
    CLEARED = "cleared"          # 已过法务，可用
    PENDING = "pending"          # 待法务判断
    REJECTED = "rejected"        # 法务否决
    NOT_ASSESSED = "not_assessed"


#: 无论法务结论如何都不予放行的取数方式
FORBIDDEN_METHODS = frozenset({AccessMethod.SCRAPING})


@dataclass(frozen=True)
class SourceRecord:
    key: str
    name: str
    access_method: str
    tos_url: str
    legal_status: str
    legal_note: str
    reviewed_on: str            # ISO 日期，人工填写
    handles_personal_info: bool = False
    handles_sensitive_pi: bool = False
    pipia_completed: bool = False

    def blockers(self) -> tuple[str, ...]:
        """返回阻止该源被调用的全部理由；为空表示可用。"""
        reasons: list[str] = []
        if self.access_method in FORBIDDEN_METHODS:
            reasons.append(
                f"取数方式为「{self.access_method}」—— 直接爬取在现行司法环境下"
                "高概率构成不正当竞争，一律不放行"
            )
        if self.legal_status != LegalStatus.CLEARED:
            reasons.append(f"法务状态为「{self.legal_status}」，未放行")
        if not self.tos_url.strip():
            reasons.append("缺少 ToS/授权依据链接")
        if not self.reviewed_on.strip():
            reasons.append("缺少法务复核日期")
        if self.handles_sensitive_pi and not self.pipia_completed:
            reasons.append(
                "涉及敏感个人信息但未完成 PIPIA —— "
                "PIPL 第55/56条要求事前评估且记录保存≥3年"
            )
        return tuple(reasons)

    @property
    def allowed(self) -> bool:
        return not self.blockers()


class SourceNotRegistered(PermissionError):
    pass


class SourceNotAllowed(PermissionError):
    pass


class Registry:
    """数据源白名单。Collector 取数前必须先过这里。"""

    def __init__(self, records: Mapping[str, SourceRecord] | None = None) -> None:
        self._records: dict[str, SourceRecord] = dict(records or {})

    def register(self, record: SourceRecord) -> None:
        self._records[record.key] = record

    def get(self, key: str) -> SourceRecord:
        if key not in self._records:
            raise SourceNotRegistered(
                f"数据源「{key}」未登记 —— 未登记的源不得调用。"
                "请先填写授权类型/ToS/法务结论/复核日期。"
            )
        return self._records[key]

    def assert_source_allowed(self, key: str) -> SourceRecord:
        """Collector 的强制入口。绕过它就是绕过合规。"""
        record = self.get(key)
        blockers = record.blockers()
        if blockers:
            raise SourceNotAllowed(
                f"数据源「{record.name}」({key}) 不予放行：\n"
                + "\n".join(f"  - {reason}" for reason in blockers)
            )
        return record

    def allowed_keys(self) -> tuple[str, ...]:
        return tuple(sorted(k for k, r in self._records.items() if r.allowed))

    def blocked_report(self) -> tuple[str, ...]:
        lines: list[str] = []
        for key in sorted(self._records):
            record = self._records[key]
            blockers = record.blockers()
            if blockers:
                lines.append(f"[{key}] {record.name}")
                lines.extend(f"    - {reason}" for reason in blockers)
        return tuple(lines)


# ---------------------------------------------------------------------------
# 初始登记表 —— 全部标为待法务判断，这是诚实的起点
# ---------------------------------------------------------------------------

INITIAL_SOURCES: tuple[SourceRecord, ...] = (
    SourceRecord(
        key="qcc_open",
        name="企查查开放平台（工商/注销吊销/经营范围高级搜索）",
        access_method=AccessMethod.OFFICIAL_API,
        tos_url="",
        legal_status=LegalStatus.PENDING,
        legal_note="官方 API，非爬虫。需确认单次成本与频次限制 —— "
                   "若按次太贵，只能对入围商机做，架构会不同。",
        reviewed_on="",
    ),
    SourceRecord(
        key="chanmama",
        name="蝉妈妈（品类 GMV / 商品数 / 达人）",
        access_method=AccessMethod.OFFICIAL_API,
        tos_url="",
        legal_status=LegalStatus.PENDING,
        legal_note="需实测报价与额度（官网已改询价）。第三方销量均为估算。",
        reviewed_on="",
    ),
    SourceRecord(
        key="feigua",
        name="飞瓜（行业榜单，交叉验证用）",
        access_method=AccessMethod.OFFICIAL_API,
        tos_url="",
        legal_status=LegalStatus.PENDING,
        legal_note="作为蝉妈妈的冗余源，防单点故障。",
        reviewed_on="",
    ),
    SourceRecord(
        key="trademark_gov",
        name="中国商标网类目申请量（领先 6–12 个月）",
        access_method=AccessMethod.PUBLIC_DOWNLOAD,
        tos_url="",
        legal_status=LegalStatus.PENDING,
        legal_note="官方公开公告。几乎无人跟踪，是最便宜的先行指标。",
        reviewed_on="",
    ),
    SourceRecord(
        key="secondhand_resale",
        name="二手平台转卖描述（后悔信号）",
        access_method=AccessMethod.SCRAPING,
        tos_url="",
        legal_status=LegalStatus.NOT_ASSESSED,
        legal_note="⚠️ 当前设想为爬取，按规则一律不放行。"
                   "若「后悔信号」确为核心差异化，必须找到授权/采购路径，"
                   "否则该能力不成立 —— 这是要在花钱前测掉的致命风险。",
        reviewed_on="",
    ),
    SourceRecord(
        key="youtube_data_api",
        name="YouTube Data API（创作者方法论，转录优先）",
        access_method=AccessMethod.OFFICIAL_API,
        tos_url="https://developers.google.com/youtube/terms/api-services-terms-of-service",
        legal_status=LegalStatus.PENDING,
        legal_note="每日 10000 配额。用 playlistItems(1单位) 而非 search(100单位)。"
                   "ToS 禁止缓存 AV 内容 —— 只存转录文本。",
        reviewed_on="",
    ),
    SourceRecord(
        key="resume_upload",
        name="用户上传简历（资源可获取性评分）",
        access_method=AccessMethod.USER_PROVIDED,
        tos_url="",
        legal_status=LegalStatus.PENDING,
        legal_note="简历非整体敏感，但身份证号/金融账户/健康字段属敏感 PI。"
                   "须单独同意 + 事前 PIPIA + 记录保存≥3年。",
        reviewed_on="",
        handles_personal_info=True,
        handles_sensitive_pi=True,
        pipia_completed=False,
    ),
)


def default_registry() -> Registry:
    """返回初始登记表。

    注意：**当前没有任何一个源是 CLEARED 状态**，
    所以 ``allowed_keys()`` 返回空。这是正确的起点 ——
    在法务过完之前，采集层根本不该能跑起来。
    """
    registry = Registry()
    for record in INITIAL_SOURCES:
        registry.register(record)
    return registry
