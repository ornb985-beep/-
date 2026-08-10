"""条目契约 —— 三轴分类 + 字段校验 + 置信档位。

## 为什么是三轴

一维分类必然吵架：「robots.txt 不可达按禁止」到底算方法、算判据、还是算合规？
三个正交轴各答一个问题，就不用吵：

    domain    它属于哪一层
    type      它是什么东西
    maturity  **它被验证到什么程度**

第三轴最重要 —— 它让「我们自己测过的」和「书上这么说的」永远分得开。
这是本知识库收录通用 AI 方法论之后，唯一能防止两者混为一谈的机制。

## 为什么置信度给档位不给数字

给 0.87 会被当成 0.87 用。这套系统在 `sdk.predict_probability`、
在 `conformal`、在 `kelly` 里都拒绝输出伪精确的点值，
知识层没有理由破例。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping, Sequence

# ---------------------------------------------------------------------------
# 轴一：domain —— 它属于哪一层
# ---------------------------------------------------------------------------


class Domain:
    ACQUISITION = "acquisition"        # 免费取数与源治理
    EVIDENCE = "evidence"              # 证据核验
    METRICS = "metrics"                # 口径、单位、时间闸
    STATISTICS = "statistics"          # 统计推断与防自欺
    ANALYSIS = "analysis"              # 商业分析引擎
    COMPLIANCE = "compliance"          # 法律与合规
    ORCHESTRATION = "orchestration"    # AI 调度体系
    DELIVERY = "delivery"              # 交付物
    GOVERNANCE = "governance"          # 门禁、失效模式、回退规则
    EXTERNAL = "external"              # 通用方法论（本项目未验证）


#: domain → 条目 ID 里的三字母代号。**改动即破坏所有既有 ID，不得修改。**
DOMAIN_CODES: Mapping[str, str] = {
    Domain.ACQUISITION: "ACQ",
    Domain.EVIDENCE: "EVD",
    Domain.METRICS: "MET",
    Domain.STATISTICS: "STA",
    Domain.ANALYSIS: "ANA",
    Domain.COMPLIANCE: "CMP",
    Domain.ORCHESTRATION: "ORC",
    Domain.DELIVERY: "DLV",
    Domain.GOVERNANCE: "GOV",
    Domain.EXTERNAL: "EXT",
}

CODE_TO_DOMAIN: Mapping[str, str] = {v: k for k, v in DOMAIN_CODES.items()}

#: 目录布局：verified 分区与 external 分区物理隔离
VERIFIED_DIR = "entries/verified"
EXTERNAL_DIR = "entries/external"


def relative_dir(domain: str) -> str:
    """条目该放在哪个目录。external 单独一区，不与已验证条目混放。"""
    if domain == Domain.EXTERNAL:
        return EXTERNAL_DIR
    return f"{VERIFIED_DIR}/{domain}"


# ---------------------------------------------------------------------------
# 轴二：type —— 它是什么东西
# ---------------------------------------------------------------------------


class Type:
    FACT = "fact"                # 关于世界的可证伪断言（需要样本）
    METHOD = "method"            # 怎么做
    CRITERION = "criterion"      # 什么时候算过 / 什么时候该停
    PARAMETER = "parameter"      # 具体取值及其来源
    ANTIPATTERN = "antipattern"  # 这样做会出事
    LESSON = "lesson"            # 我们真的踩过的坑


ALL_TYPES = (Type.FACT, Type.METHOD, Type.CRITERION,
             Type.PARAMETER, Type.ANTIPATTERN, Type.LESSON)


# ---------------------------------------------------------------------------
# 轴三：maturity —— 它被验证到什么程度
# ---------------------------------------------------------------------------


class Maturity:
    VERIFIED = "verified"        # 有实测数据或有断言它的通过测试
    IMPLEMENTED = "implemented"  # 代码写了，但没有实证支持它「有效」
    PRIOR = "prior"              # 拍定值，等真实数据校准
    FALSIFIED = "falsified"      # 被后续证据推翻
    EXTERNAL = "external"        # 外部来源，**本项目未验证**


ALL_MATURITIES = (Maturity.VERIFIED, Maturity.IMPLEMENTED, Maturity.PRIOR,
                  Maturity.FALSIFIED, Maturity.EXTERNAL)


class Status:
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    FALSIFIED = "falsified"


ALL_STATUSES = (Status.ACTIVE, Status.SUPERSEDED, Status.FALSIFIED)


class Grade:
    """证据等级。沿用 `research/dossier.py` 的 A–D 口径。"""

    A = "A"    # 法定披露、政府统计、本仓库通过的测试
    B = "B"    # 行业协会、可信媒体、一级数据商
    C = "C"    # 二手转引
    D = "D"    # 单一自媒体、无可核查出处


ALL_GRADES = (Grade.A, Grade.B, Grade.C, Grade.D)


# ---------------------------------------------------------------------------
# 置信档位
# ---------------------------------------------------------------------------


class Band:
    CONFIRMED = "CONFIRMED"
    SUPPORTED = "SUPPORTED"
    PROVISIONAL = "PROVISIONAL"
    UNVERIFIED = "UNVERIFIED"
    FALSIFIED = "FALSIFIED"


#: 关于世界的断言，样本量门槛。与 `config.MIN_SAMPLES_FOR_CALIBRATION` 同源。
MIN_SAMPLES_FOR_CONFIRMED = 30
#: 双源锚定：单源结论一律不得升到 SUPPORTED 以上。
MIN_SOURCES_FOR_SUPPORTED = 2


# ---------------------------------------------------------------------------
# 条目
# ---------------------------------------------------------------------------

ID_PATTERN = re.compile(r"^K-(ACQ|EVD|MET|STA|ANA|CMP|ORC|DLV|GOV|EXT)-\d{3}$")

#: 出现即拒绝的字段。**置信度必须是算出来的，不是填出来的。**
#: 允许手填等于允许通胀 —— 每个人都觉得自己那条挺可靠。
FORBIDDEN_FIELDS = ("confidence", "certainty", "score", "reliability", "trust")

#: 仓库外部依据用这个前缀，跳过文件存在性检查
EXTERNAL_SOURCE_PREFIX = "EXT:"

#: 正文必须出现的小节标题。**「边界」是必填的** ——
#: 没有边界的断言不是知识，是口号。
REQUIRED_SECTIONS = ("## 断言", "## 依据", "## 边界")


@dataclass(frozen=True)
class Entry:
    id: str
    title: str
    domain: str
    type: str
    maturity: str
    status: str
    evidence_grade: str
    n_independent_sources: int
    sources: tuple[str, ...]
    body: str
    path: str = ""
    sample_size: int | None = None
    supersedes: str = ""
    superseded_by: str = ""
    falsified_by: str = ""
    iteration: int = 1
    reviewed_on: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def code(self) -> str:
        return self.id.split("-")[1] if "-" in self.id else ""

    @property
    def band(self) -> str:
        return derive_band(self)

    @property
    def is_external(self) -> bool:
        return self.maturity == Maturity.EXTERNAL

    def one_line(self) -> str:
        return (f"{self.id}  [{self.band:<11}] {self.title}"
                f"  ({self.domain}/{self.type}/{self.maturity})")


def derive_band(entry: Entry) -> str:
    """从证据结构确定性地推出置信档位。**没有手填的余地。**

    这里有一处刻意的**不对称**，它是整个档位规则的核心：

        关于世界的断言（type=fact）  → 要样本量，因为它可能被下一批数据推翻
        关于本系统行为的断言        → 要代码与通过的测试，样本量无意义

    「`kelly` 在 n<30 时拒绝输出」这条不需要 30 个样本来证明，
    它需要的是一个会失败的测试。把两类混在一起用同一把尺子，
    要么冤枉了前者，要么放纵了后者。
    """
    if entry.status == Status.FALSIFIED or entry.maturity == Maturity.FALSIFIED:
        return Band.FALSIFIED
    if entry.maturity in (Maturity.PRIOR, Maturity.EXTERNAL):
        return Band.UNVERIFIED

    if entry.type == Type.FACT:
        enough_sources = entry.n_independent_sources >= MIN_SOURCES_FOR_SUPPORTED
        enough_sample = (entry.sample_size or 0) >= MIN_SAMPLES_FOR_CONFIRMED
        if entry.evidence_grade == Grade.A and enough_sources and enough_sample:
            return Band.CONFIRMED
        if entry.evidence_grade in (Grade.A, Grade.B) and enough_sources:
            return Band.SUPPORTED
        return Band.PROVISIONAL

    # 关于本系统自身行为的断言：证据是代码与测试
    if entry.maturity == Maturity.VERIFIED and entry.evidence_grade == Grade.A:
        return Band.CONFIRMED
    if (entry.maturity in (Maturity.VERIFIED, Maturity.IMPLEMENTED)
            and entry.evidence_grade in (Grade.A, Grade.B)):
        return Band.SUPPORTED
    return Band.PROVISIONAL


# ---------------------------------------------------------------------------
# 字段级校验
# ---------------------------------------------------------------------------


def validate_fields(entry: Entry) -> list[str]:
    """只做「这条条目自身是否合法」的检查。

    跨条目的检查（链完整性、id 唯一性、external 隔离）在 ``check.py``，
    因为那些需要看到全库。
    """
    problems: list[str] = []

    if not ID_PATTERN.match(entry.id):
        problems.append(f"id 格式非法「{entry.id}」—— 应为 K-<三字母域码>-<三位数字>")
    elif CODE_TO_DOMAIN.get(entry.code) != entry.domain:
        problems.append(
            f"id 的域码 {entry.code} 与 domain「{entry.domain}」不一致 —— "
            f"应为 {DOMAIN_CODES.get(entry.domain, '?')}"
        )

    if not entry.title.strip():
        problems.append("title 为空")
    if entry.domain not in DOMAIN_CODES:
        problems.append(f"未知 domain「{entry.domain}」")
    if entry.type not in ALL_TYPES:
        problems.append(f"未知 type「{entry.type}」")
    if entry.maturity not in ALL_MATURITIES:
        problems.append(f"未知 maturity「{entry.maturity}」")
    if entry.status not in ALL_STATUSES:
        problems.append(f"未知 status「{entry.status}」")
    if entry.evidence_grade not in ALL_GRADES:
        problems.append(f"未知 evidence_grade「{entry.evidence_grade}」")

    # ① 无出处不许存在
    if not entry.sources:
        problems.append(
            "sources 为空 —— 没有出处的条目不许存在。"
            "这是 grounding 纪律在知识层的复用：说不出依据的结论就是没有依据。"
        )
    if entry.n_independent_sources < 1:
        problems.append("n_independent_sources 必须 ≥1")
    if entry.n_independent_sources > len(entry.sources):
        problems.append(
            f"声称 {entry.n_independent_sources} 个独立源，但只列了 "
            f"{len(entry.sources)} 条出处 —— 独立源数不能凭空多出来"
        )

    # ④ 证伪必须留下推翻它的证据
    if entry.status == Status.FALSIFIED and not entry.falsified_by:
        problems.append(
            "status=falsified 但缺 falsified_by —— "
            "证伪不删除，但必须指出是什么推翻了它，否则查不到「为什么错」"
        )
    if entry.falsified_by and entry.status != Status.FALSIFIED:
        problems.append("有 falsified_by 却不是 falsified 状态 —— 状态与证据不一致")
    if entry.status == Status.SUPERSEDED and not entry.superseded_by:
        problems.append("status=superseded 但缺 superseded_by")

    if entry.iteration < 1:
        problems.append("iteration 必须 ≥1")
    if entry.supersedes and entry.iteration < 2:
        problems.append("取代了旧条目却仍是 iteration=1 —— 叠加进化必须体现在版次上")

    # external 分区隔离（自身侧）
    if entry.domain == Domain.EXTERNAL and entry.maturity != Maturity.EXTERNAL:
        problems.append(
            f"external 分区的条目 maturity 必须是 external，实际「{entry.maturity}」"
            " —— 未经本项目验证的内容不得伪装成已验证"
        )
    if entry.maturity == Maturity.EXTERNAL and entry.evidence_grade == Grade.A:
        problems.append(
            "external 条目不得标 A 级证据 —— A 级留给法定披露、政府统计、"
            "以及本仓库通过的测试"
        )

    for section in REQUIRED_SECTIONS:
        if section not in entry.body:
            problems.append(f"正文缺少必填小节「{section}」")

    return problems


def next_id(domain: str, existing: Sequence[str]) -> str:
    """给某个域分配下一个可用 ID。**只增不复用** —— 删掉的号不许再发。"""
    code = DOMAIN_CODES.get(domain)
    if code is None:
        raise ValueError(f"未知 domain: {domain}")
    used = [int(e.split("-")[2]) for e in existing
            if ID_PATTERN.match(e) and e.split("-")[1] == code]
    return f"K-{code}-{(max(used) + 1) if used else 1:03d}"
