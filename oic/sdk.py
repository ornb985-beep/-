"""OIC SDK —— 把这套分析能力嵌进你自己的 App / 智能体。

## 一句话

    from oic.sdk import OIC
    oic = OIC.for_app(app_name="我的商机助手", contact="you@example.com")

之后所有能力都挂在 ``oic`` 上，**且所有闸门都在里面，绕不过去**。

## 设计原则：SDK 不是把内核暴露出来，是把纪律一起打包

如果 SDK 只是 ``import`` 转发，那么你的 App 里任何一次
「这次先跳过 audit」「这次先不加 AI 标识」都会成立 ——
而赶进度的时候一定会有人这么写。

所以这里的每个方法都是**成对的**：

    ability(...)              能力
    → 前置不满足时抛 Refusal   而不是返回退化结果

具体地：

    ``score()``    输入不完整 → 抛，不给默认值
    ``predict()``  已解析结局 < 30 → 抛 ``NotCalibrated``，不给"置信度低"的点值
    ``export()``   **唯一出口**，强制过证券边界 + AI 双标识
    ``fetch()``    强制过 provenance 白名单 + robots.txt

## 三段式流程（你给的框架）在 SDK 里的位置

    ① 全平台取数     plan_investigation() → fetch() / parse_feed()
    ② 智能体分类分析  observe() → audit() → dossier()
    ③ 操盘手复审      score() → rank() → business_plan() → export()

②→③ 之间有一道硬闸：``audit()`` 报 ERROR 的品类，``dossier()`` 拒绝放行。
这是为了防止我自己犯过的那类错（把「3.81万」记成 3,810,000）流到下游。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from oic import SCORING_ENGINE_VERSION, __version__
from oic.calibration.brier import calibration_status
from oic.compliance import ai_labeling
from oic.compliance.provenance import (
    LegalStatus, Registry, SourceRecord, default_registry,
)
from oic.compliance.securities_guard import assert_safe, guard
from oic.config import Config, DEFAULT_CONFIG, MIN_SAMPLES_FOR_CALIBRATION
from oic.evidence.grounding import Claim, GroundingResult, verify_claim
from oic.research import investigate as inv
from oic.research.audit import AuditReport, Severity, audit as _audit
from oic.research.dossier import Observation
from oic.scoring.engine import (
    OpportunityInput, ScoreResult, compute_all_scores, rank_opportunities,
    verify_scores,
)
from oic.sources.http_fetch import (
    FetchPolicy, FetchResult, HttpFetcher, Transport, html_to_text,
)
from oic.sources.rss import FeedItem, filter_by_date, parse_feed

__all__ = [
    "OIC", "Refusal", "NotCalibrated", "DataRejected", "SourceBlocked",
    "Capability", "CapabilityReport", "UNFILED_PREFIX",
]

#: 未填算法备案号时的占位前缀。**故意让它出现在导出元数据里** ——
#: 一个看起来像真编码的默认值会被原样带上线，一个带 UNFILED- 的不会。
UNFILED_PREFIX = "UNFILED-"


# ---------------------------------------------------------------------------
# 拒绝 —— 在 App 里应当被当作正常分支处理，不是异常情况
# ---------------------------------------------------------------------------


class Refusal(RuntimeError):
    """系统拒绝输出。

    **这是设计的一部分，不是故障。** 在你的 App 里应当把它渲染成
    「暂不能给结论，因为 ⋯⋯」，而不是 catch 掉然后填个默认值。
    """


class NotCalibrated(Refusal):
    """已解析结局不足，概率类输出一律拒绝。"""


class DataRejected(Refusal):
    """数据没过纠错内核，下游拒绝使用。"""


class SourceBlocked(Refusal):
    """数据源未登记或未放行。"""


# ---------------------------------------------------------------------------
# 能力自陈 —— 「这套东西现在到底能不能用」必须能被程序问出来
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Capability:
    key: str
    name: str
    available: bool
    reason: str

    def line(self) -> str:
        return f"{'✅' if self.available else '⬜'} {self.name} —— {self.reason}"


@dataclass(frozen=True)
class CapabilityReport:
    engine_version: int
    package_version: str
    n_resolved_outcomes: int
    capabilities: tuple[Capability, ...]

    @property
    def available_keys(self) -> tuple[str, ...]:
        return tuple(c.key for c in self.capabilities if c.available)

    def lines(self) -> tuple[str, ...]:
        head = (f"OIC v{self.package_version} · 计算层 v{self.engine_version} · "
                f"已解析结局 {self.n_resolved_outcomes} 条")
        return (head,) + tuple(c.line() for c in self.capabilities)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


@dataclass
class OIC:
    """嵌入式客户端。

    ``registry`` 默认是 provenance 的初始登记表 —— **里面没有任何源是
    CLEARED 状态**，所以 ``fetch()`` 一开始会全部拒绝。这是正确的起点：
    在你为每个源填上授权依据与法务结论之前，采集层本就不该能跑。
    用 ``clear_source()`` 逐个放行，每次放行都要留下依据。
    """

    provider: ai_labeling.ProviderIdentity
    registry: Registry = field(default_factory=default_registry)
    config: Config = DEFAULT_CONFIG
    fetch_policy: FetchPolicy | None = None
    _fetcher: HttpFetcher | None = field(default=None, repr=False)

    # -- 构造 --------------------------------------------------------------

    @classmethod
    def for_app(
        cls,
        app_name: str,
        contact: str,
        provider_code: str = "",
        version: str = "1.0",
        config: Config = DEFAULT_CONFIG,
        registry: Registry | None = None,
    ) -> "OIC":
        """给你的 App 建一个客户端。

        ``contact`` 是必填的邮箱或主页 —— 它会写进 User-Agent。
        SEC 等来源明文要求可识别身份；更重要的是，
        **可被联系的抓取方在争议中处于完全不同的位置**。

        ``provider_code`` 应填你的**算法备案号**（GB 45438-2025 的隐式标识
        要求真实的服务提供者编码）。不填不会报错 —— 开发期需要能跑起来 ——
        但会被打上 ``UNFILED-`` 前缀，且 ``capabilities()`` 里
        ``aigc_filing`` 一项会显示为未就绪。**上线前必须换成真号。**
        """
        if not contact or not contact.strip():
            raise ValueError(
                "contact 必填 —— 它进 User-Agent，是「善意抓取」最基本的证据"
            )
        ua_contact = contact if contact.startswith("http") else f"mailto:{contact}"
        policy = FetchPolicy(
            user_agent=f"{_ua_token(app_name)}/{version} (+{ua_contact})"
        )
        return cls(
            provider=ai_labeling.ProviderIdentity(
                name=app_name,
                code=provider_code or f"{UNFILED_PREFIX}{_ua_token(app_name).upper()}",
            ),
            registry=registry or default_registry(),
            config=config,
            fetch_policy=policy,
        )

    # -- ① 取数 ------------------------------------------------------------

    def clear_source(self, key: str, tos_url: str, legal_note: str,
                     reviewed_on: str) -> SourceRecord:
        """把某个源改为「法务已放行」。

        四个参数全部必填且会被校验 —— 因为放行的价值全在依据上，
        没有 ToS 链接和复核日期的放行，等于没放行。

        ⚠️ ``access_method == SCRAPING`` 的源**无论如何都不会被放行**：
        那是 ``blockers()`` 里的硬规则，不是这里能覆盖的。
        """
        record = self.registry.get(key)
        for name, value in (("tos_url", tos_url), ("legal_note", legal_note),
                            ("reviewed_on", reviewed_on)):
            if not value or not value.strip():
                raise ValueError(f"{name} 必填 —— 放行的价值全在依据上")
        cleared = SourceRecord(
            key=record.key, name=record.name, access_method=record.access_method,
            tos_url=tos_url, legal_status=LegalStatus.CLEARED, legal_note=legal_note,
            reviewed_on=reviewed_on,
            handles_personal_info=record.handles_personal_info,
            handles_sensitive_pi=record.handles_sensitive_pi,
            pipia_completed=record.pipia_completed,
        )
        self.registry.register(cleared)
        return cleared

    def source_status(self) -> tuple[str, ...]:
        """现在哪些源能用、哪些不能用、为什么。直接可以渲染进你的 App。"""
        allowed = self.registry.allowed_keys()
        lines = [f"已放行 {len(allowed)} 个源：{'、'.join(allowed) or '（无）'}"]
        lines.extend(self.registry.blocked_report())
        return tuple(lines)

    def fetcher(self, transport: Transport | None = None) -> HttpFetcher:
        """通用 HTTP 取数器（robots.txt + 限速 + 条件请求）。"""
        if self._fetcher is None or transport is not None:
            if self.fetch_policy is None:
                raise ValueError("未配置 FetchPolicy —— 请用 OIC.for_app() 构造")
            self._fetcher = HttpFetcher(self.fetch_policy, self.registry,
                                        transport=transport)
        return self._fetcher

    def fetch(self, url: str, source_key: str) -> FetchResult:
        """抓一个页面。白名单 → robots → 限速 → 条件请求，四道闸全过才返回。"""
        try:
            return self.fetcher().fetch(url, source_key)
        except PermissionError as exc:
            raise SourceBlocked(str(exc)) from exc

    def read_feed(self, xml_text: str, source_key: str,
                  as_of: str | None = None) -> tuple[FeedItem, ...]:
        """解析 RSS/Atom。``as_of`` 给了就按它过滤，**无日期条目一律排除**。"""
        self.registry.assert_source_allowed(source_key)
        items = parse_feed(xml_text, source_key)
        return filter_by_date(items, as_of) if as_of else items

    # -- ② 深度调查与纠错 ---------------------------------------------------

    def plan_investigation(self, category: str, years: Sequence[int],
                           have_metrics: Iterable = ()) -> inv.InvestigationPlan:
        """生成八角度查询矩阵。你的智能体拿去跑检索，结果回填 ``observe()``。"""
        return inv.plan_investigation(category, years, have_metrics)

    def assess_independence(self, sources: Sequence[tuple[str, str]]
                            ) -> inv.IndependenceReport:
        """``sources`` 是 (来源名, 原文片段)。把「几个源」折成「几个独立源」。"""
        nodes = tuple(inv.SourceNode(name, snippet) for name, snippet in sources)
        return inv.assess_independence(nodes)

    def assess_saturation(self, yields: Sequence[tuple[str, int]]
                          ) -> inv.SaturationReport:
        """判断「还该不该继续查」。饱和 = 连续 3 次边际产出 < 5%。"""
        return inv.assess_saturation(yields)

    def check_claim(
        self,
        value: float,
        raw_text: str,
        snippet: str,
        metric: str = "",
        unit: str = "",
        source_url: str = "",
    ) -> GroundingResult:
        """字符级回验：这个数字真的在原文的这一段里吗。

        **这是唯一能抓住手工转录数量级错误的检查。**
        我自己在这个仓库里犯过一次：把「3.81万」记成 3,810,000，
        因为检索摘要把「万」译成了 million。走这条就当场拦下。

        ``snippet`` 必须是 ``raw_text`` 的**原样子串** —— 定位靠字符偏移，
        改过一个字都定位不到，那正是要拦的情况。
        """
        start = raw_text.find(snippet)
        if start < 0:
            raise DataRejected(
                "片段不是原文的子串 —— 无法定位，拒绝校验。"
                "证据必须能用字符偏移回到原文，否则「有出处」只是说法。"
            )
        claim = Claim(
            claim_id=f"{metric or 'claim'}@{start}",
            metric=metric or "未命名指标", value=value, unit=unit,
            span_start=start, span_end=start + len(snippet),
            source_url=source_url, snapshot_hash="",
        )
        return verify_claim(claim, raw_text)

    def audit(self, observations: Sequence[Observation]) -> AuditReport:
        """六项确定性检查。**不用 LLM** —— 让犯错者当裁判是没有意义的。"""
        return _audit(observations)

    def assert_data_usable(self, observations: Sequence[Observation]
                           ) -> Sequence[Observation]:
        """纠错内核的硬闸：有 ERROR 就拒绝放行，不是「警告后继续」。"""
        report = self.audit(observations)
        errors = [f for f in report.findings if f.severity == Severity.ERROR]
        if errors:
            detail = "\n".join(f.line() for f in errors[:10])
            raise DataRejected(
                f"纠错内核报出 {len(errors)} 条 ERROR，数据不予放行：\n{detail}\n"
                "修数据，不要跳过这道闸 —— 错数据上建的一切结论都是错的。"
            )
        return observations

    # -- ③ 评分与排序 -------------------------------------------------------

    def score(self, opportunity: OpportunityInput) -> ScoreResult:
        """确定性打分。**内部无网络、无时钟、无随机**（铁律 1）。"""
        return compute_all_scores(opportunity, self.config)

    def verify_reproducible(self, opportunity: OpportunityInput) -> ScoreResult:
        """双跑并断言逐字节一致（G0 门）。上线前跑一次，别信「应该一样」。"""
        return verify_scores(opportunity, self.config)

    def rank(self, opportunities: Sequence[OpportunityInput]
             ) -> tuple[ScoreResult, ...]:
        return rank_opportunities(opportunities, self.config)

    # -- 概率类输出：样本不足一律拒绝 ---------------------------------------

    def predict_probability(self, score: float, n_resolved: int) -> float:
        """score → 成功概率。**n < 30 直接抛 NotCalibrated。**

        为什么不给个「置信度低」的点值：因为产品里没有人会读那行小字，
        而一个编出来的 42% 会被当成 42% 用。拒绝比标注诚实。
        """
        if n_resolved < MIN_SAMPLES_FOR_CALIBRATION:
            raise NotCalibrated(
                f"已解析结局仅 {n_resolved} 条 < {MIN_SAMPLES_FOR_CALIBRATION}，"
                f"当前校准状态「{calibration_status(n_resolved)}」。\n"
                "不输出概率点值 —— 此时的任何数字都是编的。\n"
                "可用的替代：score 的相对排序（序关系不需要校准）、"
                "以及带可证伪条件的区间。"
            )
        raise NotCalibrated(
            "映射函数尚未在 ≥30 条真实结局上拟合 —— "
            "样本够了不等于已经拟合。请先跑 oic.research.backtest 出映射。"
        )

    # -- ④ 出口：唯一的对外通道 --------------------------------------------

    def export(self, body: str, generated_at: str,
               extra: Mapping[str, str] | None = None) -> ai_labeling.LabeledContent:
        """**唯一出口。** 任何要给到用户眼前的文本都必须走这里。

        顺序是固定的：

            证券边界（S1–S4 硬违规直接抛）→ AI 双标识 → 标识校验

        S5（措辞）会被自动改写；S1–S4 **不做自动改写** ——
        改写只会掩盖问题，这类内容根本不该被生成出来。
        """
        safe_body = assert_safe(body)
        content = ai_labeling.label(safe_body, self.provider, generated_at, extra)
        ai_labeling.assert_labeled(content)
        return content

    def check_export(self, body: str) -> tuple[str, ...]:
        """预检：不抛异常，只返回会拦在哪。给你的 App 做实时提示用。"""
        return guard(body).report()

    # -- ⑤ 能力自陈 --------------------------------------------------------

    def capabilities(self, n_resolved_outcomes: int = 0) -> CapabilityReport:
        """诚实回答「现在这套东西能干什么」。

        这个方法存在的理由：用户问过「这个模型是万无一失的了吧」。
        答案是否定的，而否定必须能被程序读出来，不能只写在文档里。
        """
        allowed = self.registry.allowed_keys()
        calibrated = n_resolved_outcomes >= MIN_SAMPLES_FOR_CALIBRATION
        filed = not self.provider.code.startswith(UNFILED_PREFIX)
        caps = (
            Capability("scoring", "确定性打分与排序", True,
                       "纯计算，可复现，不依赖样本量"),
            Capability("audit", "数据纠错内核（6 项确定性检查）", True,
                       "不用 LLM，随时可用"),
            Capability("investigate", "八角度深度调查计划", True,
                       "生成查询矩阵；实际检索由你的 App 执行"),
            Capability("compliance", "证券边界 + AI 双标识", True,
                       "导出路径强制经过"),
            Capability("aigc_filing", "AIGC 服务提供者编码", filed,
                       f"编码 {self.provider.code}" if filed else
                       f"当前为占位编码 {self.provider.code} —— "
                       "GB 45438-2025 要求真实算法备案号，上线前必须替换"),
            Capability("fetch", "合规取数", bool(allowed),
                       f"已放行 {len(allowed)} 个源"
                       if allowed else "尚无已放行的源 —— 请先 clear_source()"),
            Capability("probability", "成功概率预测", calibrated,
                       f"已解析结局 {n_resolved_outcomes} 条"
                       + ("，可校准" if calibrated
                          else f" < {MIN_SAMPLES_FOR_CALIBRATION}，拒绝输出概率")),
            Capability("kelly", "仓位建议（Kelly）", calibrated,
                       "同上：样本不足时拒绝，不给保守默认值"),
            Capability("effectiveness", "「本系统有效」这一主张", False,
                       "G2 门（BSS<UNC 且 n≥30）尚未通过 —— "
                       "在此之前不得对外声称有效性"),
        )
        return CapabilityReport(
            engine_version=SCORING_ENGINE_VERSION,
            package_version=__version__,
            n_resolved_outcomes=n_resolved_outcomes,
            capabilities=caps,
        )


def _ua_token(name: str) -> str:
    """把 App 名压成 UA 里能用的 token（去空格与非 ASCII）。"""
    token = "".join(ch for ch in name if ch.isascii() and (ch.isalnum() or ch in "-_"))
    return token or "OIC-App"


# ---------------------------------------------------------------------------
# 便捷：把 HTML/RSS 变成可回验的文本
# ---------------------------------------------------------------------------

def to_text(result: FetchResult) -> str:
    """FetchResult → 纯文本。HTML 自动去标签，**不做正文抽取**。

    正文抽取算法会丢段落，而丢掉的可能正是含数字的那一段。
    宁可留噪声，也不让证据凭空消失。
    """
    return result.as_text()


def strip_html(html_text: str) -> str:
    return html_to_text(html_text)
