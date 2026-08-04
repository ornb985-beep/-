"""配置层 —— 所有阈值、权重、赛道参数集中于此。

原则：
  * 提示词里不写死任何阈值，全部从这里读。
  * 每个未经真实数据校准的数字标注 PRIOR，界面必须显示"未校准"。
  * 赛道相关的一切（Outcome 标签、门槛、数据源）放 TrackProfile，
    换赛道 = 改一个字符串，不改任何计算代码。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping

# ---------------------------------------------------------------------------
# 校准状态门禁
# ---------------------------------------------------------------------------

#: 已解析真实结局数少于此值时，禁止宣称"已校准"，且 Kelly 拒绝输出仓位。
#: 依据：PDF 主题一第 7 节 —— <30–50 个样本时 REL/ECE 方差极大。
MIN_SAMPLES_FOR_CALIBRATION = 30

#: 分层贝叶斯借力所需的最小品类内样本；低于此值完全依赖全局先验。
MIN_SAMPLES_PER_CATEGORY = 5


# ---------------------------------------------------------------------------
# 权重（可被影子权重机制学习修正）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Weights:
    """CODE 四维权重。基准均为 25，公式系数 = 基准系数 × (权重/25)。

    ``resource`` 不在此处 —— 资源系数恒为 0.2，永不被学习稀释
    （资源约束是物理事实，不因用户偏好改变）。
    """

    c: float = 25.0
    o: float = 25.0
    d: float = 25.0
    e: float = 25.0

    #: 单维权重上限，防止一次误否决把某维推到支配地位
    cap: float = 40.0

    def bumped(self, dimension: str, delta: float = 2.0) -> "Weights":
        """返回某一维加权后的新 Weights（不可变，便于影子权重做 A/B）。"""
        if dimension not in ("c", "o", "d", "e"):
            raise ValueError(f"未知维度: {dimension}")
        current = getattr(self, dimension)
        return replace(self, **{dimension: min(current + delta, self.cap)})


BASELINE_WEIGHT = 25.0

#: 资源匹配度在可行性中的系数。硬编码，不参与学习。
RESOURCE_COEFF = 0.2


# ---------------------------------------------------------------------------
# 供给侧引擎参数（全部 PRIOR，等真实数据校准）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SupplyParams:
    """剪刀差与死亡率参数。

    PRIOR: 以下全部为拍定值，未经任何真实数据校准。
    校准前不得作为硬阈值对外宣称。
    """

    #: 死亡率放大系数，风险系数 = 1 − min(X × k, 0.5)
    death_rate_k: float = 1.0

    #: M 系数分档边界（百分点）
    m_strong: float = 30.0
    m_open: float = 10.0
    m_balanced: float = -10.0
    m_meatgrinder: float = -30.0

    #: M 系数取值
    coeff_strong: float = 1.3
    coeff_open: float = 1.1
    coeff_balanced: float = 1.0
    coeff_crowding: float = 0.7

    #: 触发"绞肉机"红线所需的死亡率阈值
    high_death_rate: float = 0.15

    #: Schwartz 成熟度分级的同类企业数边界
    soph_l1_max: int = 10
    soph_l2_max: int = 50
    soph_l3_max: int = 200

    calibrated: bool = False


# ---------------------------------------------------------------------------
# 红线阈值
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RedlineParams:
    """任一触发即排序分归零，不可被高分抵消。"""

    #: HHI 高度集中门槛（份额用百分数，Σ share² ）
    hhi_concentrated: float = 1800.0
    #: 与高集中同时成立才触发的机会分下限（Ulwick 量表 0–20）
    opportunity_floor: float = 15.0
    #: 刷单风险分（0–100）超过即视为数据不可信
    fake_review_max: float = 60.0

    calibrated: bool = False


# ---------------------------------------------------------------------------
# 变现系数（pathCoeff）
# ---------------------------------------------------------------------------

#: 有真实成交证据
PATH_COEFF_PROVEN = 1.2
#: 有明确付费意愿信号
PATH_COEFF_INTENT = 1.0
#: 仅讨论热度
PATH_COEFF_BUZZ = 0.8

#: 成交证据关键词（须来自 A/B 级来源才生效，见 scoring.dimensions）
PROVEN_PATTERNS = (
    "GMV", "月销", "年营收", "营收破", "销售额", "销量", "万单", "付费用户", "ARR",
)
INTENT_PATTERNS = (
    "付费", "客单价", "溢价", "接受度", "愿意", "买单", "询价",
)


# ---------------------------------------------------------------------------
# 来源分级
# ---------------------------------------------------------------------------

#: A=官方/财报, B=权威媒体, C=自媒体。C 级只作线索，永不参与变现系数判定。
SOURCE_GRADES = ("A", "B", "C")
#: 允许参与变现系数判定的来源等级
PATH_COEFF_ELIGIBLE_GRADES = frozenset({"A", "B"})
#: 视为已锚定所需的独立来源数
MIN_INDEPENDENT_SOURCES = 2
#: 媒体数字与官方统计偏差超过此比例即自动降权
SOURCE_DIVERGENCE_LIMIT = 0.30


# ---------------------------------------------------------------------------
# 证据时效衰减
# ---------------------------------------------------------------------------

#: 指数衰减 w = e^(−λt)，t 单位为天。PRIOR，按品类校准。
DEFAULT_DECAY_LAMBDA = 0.0077  # 半衰期约 90 天


# ---------------------------------------------------------------------------
# 多 agent 门禁（铁律 2）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentGate:
    """铁律 2 的代码级执行：没有实测基线，不准扩多智能体。

    Google + MIT 的"45% 规则"：单 agent 准确率超过约 45% 后，
    加 agent 收益递减甚至转负；顺序推理任务实测倒退 39–70%。
    """

    #: 单 agent 实测准确率。None = 尚未测量。
    baseline_accuracy: float | None = None
    #: 超过此准确率则不得扩展多智能体
    threshold: float = 0.45
    #: 任务是否可拆成独立并行子任务
    task_is_parallelizable: bool = False

    def multi_agent_allowed(self) -> bool:
        """未测基线一律返回 False —— 这是防止"把好东西全加上"的纪律。"""
        if self.baseline_accuracy is None:
            return False
        if not self.task_is_parallelizable:
            return False
        return self.baseline_accuracy < self.threshold

    def reason(self) -> str:
        if self.baseline_accuracy is None:
            return "单 agent 基线未测量 —— 按铁律 2 禁止扩展多智能体"
        if not self.task_is_parallelizable:
            return "任务为顺序推理链 —— 应用单 agent + Chain-of-Verification"
        if self.baseline_accuracy >= self.threshold:
            return (
                f"单 agent 准确率 {self.baseline_accuracy:.0%} ≥ {self.threshold:.0%}"
                " —— 优化提示词与验证，不要加 agent"
            )
        return "满足扩展条件"


# ---------------------------------------------------------------------------
# 对抗污染检测（默认全部关闭）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PollutionDetectors:
    """默认关闭。必须在真实数据上标定阈值并通过对抗 eval 集后才允许开启。

    * Benford 要求跨数量级的自然分布；电商有价格分档与平台舍入，直接用会误伤。
    * 突变点检测在 618/双11 期间会大量误报。
    """

    benford_enabled: bool = False
    changepoint_enabled: bool = False
    template_cluster_enabled: bool = False
    thresholds_calibrated: bool = False


# ---------------------------------------------------------------------------
# 赛道 profile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrackProfile:
    """赛道相关参数。换赛道只改这里，计算代码完全无关。"""

    key: str
    name: str
    #: Outcome 表的成功标签定义（人可读，写入预测存档以防口径漂移）
    outcome_label: str
    #: 从预测到可解析结局的天数
    resolution_days: int
    #: 快通道代理结局（只用于实验排序，不写入校准）
    surrogate_label: str
    surrogate_days: int
    #: 该赛道的基础率先验（PRIOR，等真实数据替换）
    base_rate_prior: float
    stage_gates: tuple[tuple[str, int, str], ...] = ()


CONSUMER_GOODS = TrackProfile(
    key="consumer_goods",
    name="爆品选品 / 实物电商",
    outcome_label="上架 90 天后月销 ≥500 单",
    resolution_days=90,
    surrogate_label="落地页 7 天留资率 ≥15%",
    surrogate_days=7,
    base_rate_prior=0.12,
    stage_gates=(
        ("选品验证", 7, "打样 5-10 款 + 3 条短视频测流量"),
        ("小批量试销", 21, "转化率 >3%、退货率 <15%"),
        ("规模化", 45, "锁定爆款 + 达人铺量 + 供应链降本 20%"),
        ("品牌化", 90, "月销 500+ 单、复购率 >20%"),
    ),
)

AI_SAAS = TrackProfile(
    key="ai_saas",
    name="AI 工具 / SaaS",
    outcome_label="60 天内 MRR ≥2 万元",
    resolution_days=60,
    surrogate_label="候补名单 14 天 ≥200 人",
    surrogate_days=14,
    base_rate_prior=0.08,
    stage_gates=(
        ("MVP", 14, "只做一个功能"),
        ("种子验证", 30, "50 个用户、周活 >40%、NPS >30"),
        ("付费转化", 60, "MRR 破 2 万"),
        ("规模化", 90, "MRR 破 10 万"),
    ),
)

TRACKS: Mapping[str, TrackProfile] = {
    CONSUMER_GOODS.key: CONSUMER_GOODS,
    AI_SAAS.key: AI_SAAS,
}

DEFAULT_TRACK = CONSUMER_GOODS.key


# ---------------------------------------------------------------------------
# 顶层配置
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    weights: Weights = field(default_factory=Weights)
    supply: SupplyParams = field(default_factory=SupplyParams)
    redlines: RedlineParams = field(default_factory=RedlineParams)
    agent_gate: AgentGate = field(default_factory=AgentGate)
    detectors: PollutionDetectors = field(default_factory=PollutionDetectors)
    track_key: str = DEFAULT_TRACK
    decay_lambda: float = DEFAULT_DECAY_LAMBDA

    @property
    def track(self) -> TrackProfile:
        return TRACKS[self.track_key]

    def uncalibrated_notice(self) -> str | None:
        """界面必须显示的诚实标注；全部校准完成返回 None。"""
        pending = []
        if not self.supply.calibrated:
            pending.append("供给侧参数(k/M分档)")
        if not self.redlines.calibrated:
            pending.append("红线阈值")
        if not self.detectors.thresholds_calibrated:
            pending.append("污染检测阈值")
        if not pending:
            return None
        return "以下参数未经真实数据校准，仅为先验值：" + "、".join(pending)


DEFAULT_CONFIG = Config()
