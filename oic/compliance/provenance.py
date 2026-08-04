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
    # -----------------------------------------------------------------
    # 热榜 / 注意力源
    #
    # ⚠️ 这一组全部只测「需求侧注意力」。它们回答不了
    #    「供给增速是多少」，因此单靠它们算不出剪刀差。
    #    见 scoring/attention.py 的结构约束。
    # -----------------------------------------------------------------
    SourceRecord(
        key="weibo_hot",
        name="微博热搜榜",
        access_method=AccessMethod.SCRAPING,
        tos_url="https://weibo.com/signup/v5/protocol",
        legal_status=LegalStatus.NOT_ASSESSED,
        legal_note="⚠️ 该站有反爬措施。反爬 = 技术管理措施，"
                   "《反不正当竞争法》(2025) 第13条第3款禁止以避开或破坏"
                   "技术管理措施的方式获取他人合法持有的数据。"
                   "**抓取失败不是待修的 bug，是停止信号。**"
                   "若确需该数据，只能走官方开放平台或商业授权。",
        reviewed_on="",
    ),
    SourceRecord(
        key="zhihu_hot",
        name="知乎热榜",
        access_method=AccessMethod.SCRAPING,
        tos_url="https://www.zhihu.com/term/zhihu-terms",
        legal_status=LegalStatus.NOT_ASSESSED,
        legal_note="同微博：有反爬措施，持续绕过存在法律风险。"
                   "需改走授权渠道，或从源清单中移除。",
        reviewed_on="",
    ),
    SourceRecord(
        key="baidu_hot",
        name="百度热搜",
        access_method=AccessMethod.SCRAPING,
        tos_url="",
        legal_status=LegalStatus.NOT_ASSESSED,
        legal_note="当前可抓通不等于合规。需确认取数方式："
                   "若为页面抓取则同样受第13条第3款约束；"
                   "百度指数有官方开放接口，应优先走那条路。",
        reviewed_on="",
    ),
    SourceRecord(
        key="toutiao_hot",
        name="今日头条热榜",
        access_method=AccessMethod.SCRAPING,
        tos_url="",
        legal_status=LegalStatus.NOT_ASSESSED,
        legal_note="同上：能抓通 ≠ 获授权。需登记实际取数方式与依据。",
        reviewed_on="",
    ),
    SourceRecord(
        key="douyin_hot",
        name="抖音热点榜",
        access_method=AccessMethod.SCRAPING,
        tos_url="https://www.douyin.com/agreements",
        legal_status=LegalStatus.NOT_ASSESSED,
        legal_note="抖音开放平台有官方接口。作为核心赛道（珠宝直播）的主源，"
                   "尤其应走官方授权 —— 平台依赖本身也是 R1 红线的一类。",
        reviewed_on="",
    ),
    # -----------------------------------------------------------------
    # RSS —— 发布方主动提供，合规性显著优于抓取
    # -----------------------------------------------------------------
    SourceRecord(
        key="rss_36kr",
        name="36氪 RSS（创投 / 新品牌 / 融资）",
        access_method=AccessMethod.PUBLIC_DOWNLOAD,
        tos_url="",
        legal_status=LegalStatus.PENDING,
        legal_note="RSS 由发布方主动提供，是「被邀请读取」而非「绕过措施」，"
                   "合规位置远好于页面抓取。仍需确认转载与二次分发条款。"
                   "内容属媒体叙事（B级），**不是供给侧数据**。",
        reviewed_on="",
    ),
    SourceRecord(
        key="rss_huxiu",
        name="虎嗅 RSS（商业 / 消费）",
        access_method=AccessMethod.PUBLIC_DOWNLOAD,
        tos_url="",
        legal_status=LegalStatus.PENDING,
        legal_note="同 36氪。媒体叙事，B级来源。",
        reviewed_on="",
    ),
    SourceRecord(
        key="rss_iyiou",
        name="亿欧 RSS（产业 / 科技）",
        access_method=AccessMethod.PUBLIC_DOWNLOAD,
        tos_url="",
        legal_status=LegalStatus.PENDING,
        legal_note="同 36氪。媒体叙事，B级来源。",
        reviewed_on="",
    ),
    # -----------------------------------------------------------------
    # 政府 / 法定公开 —— A 级，且部分是稀缺的供给侧数据
    # -----------------------------------------------------------------
    SourceRecord(
        key="stats_gov",
        name="国家统计局（宏观消费、社零、CPI）",
        access_method=AccessMethod.PUBLIC_DOWNLOAD,
        tos_url="http://www.stats.gov.cn/",
        legal_status=LegalStatus.PENDING,
        legal_note="法定公开统计数据，A 级。"
                   "注意：**仍属需求侧**，且颗粒度到行业大类，"
                   "落不到品类层，不能替代供给侧数据。",
        reviewed_on="",
    ),
    SourceRecord(
        key="gsxt_gov",
        name="国家企业信用信息公示系统（注册 / 注销 / 吊销）",
        access_method=AccessMethod.PUBLIC_DOWNLOAD,
        tos_url="https://www.gsxt.gov.cn/",
        legal_status=LegalStatus.PENDING,
        legal_note="**这是剪刀差缺的那一半。** 法定公示信息，A 级，"
                   "含企业注册与注销吊销 —— 供给侧的权威来源。"
                   "⚠️ 该站有验证码与频率限制，直接抓取同样受第13条第3款约束；"
                   "合规路径是官方查询或走已获授权的商业数据方（企查查/天眼查）。",
        reviewed_on="",
    ),
    SourceRecord(
        key="bidding_gov",
        name="全国公共资源交易平台（招投标）",
        access_method=AccessMethod.PUBLIC_DOWNLOAD,
        tos_url="",
        legal_status=LegalStatus.PENDING,
        legal_note="法定公开招投标信息。可作 B 端需求的先行指标，"
                   "也能反映某品类的采购方数量（弱供给侧信号）。",
        reviewed_on="",
    ),
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
        key="sec_edgar",
        name="美国 SEC EDGAR（S-1 / 10-K 招股书与年报）",
        access_method=AccessMethod.PUBLIC_DOWNLOAD,
        tos_url="https://www.sec.gov/os/webmaster-faq#developers",
        legal_status=LegalStatus.PENDING,
        legal_note="法定公开披露文件，非爬取。SEC 明文允许程序化访问，"
                   "但要求 User-Agent 含联系邮箱且 ≤10 请求/秒 —— "
                   "这是 ToS 硬要求，违反会被封禁。"
                   "内容为审计过、有法律责任的 A 级数据。",
        reviewed_on="",
    ),
    SourceRecord(
        key="cninfo",
        name="巨潮资讯网（A股招股说明书 / 年报，证监会指定披露平台）",
        access_method=AccessMethod.PUBLIC_DOWNLOAD,
        tos_url="",
        legal_status=LegalStatus.PENDING,
        legal_note="证监会指定的法定信息披露平台，公告为强制公开内容。"
                   "「行业竞争格局」章节含市占率/CR5/同业企业数 —— "
                   "正是公开渠道拿不到、而剪刀差必需的供给侧字段。"
                   "需确认其 robots 与访问频率要求。",
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
