"""差异化与需求分层 —— Ulwick 机会分 + Berger Better-Worse 系数。

存在的理由：避免"我觉得更好"。

禀赋效应实证：卖方普遍高估自身产品价值 —— 普通私人商品 WTA/WTP
比值均值约 2.9（Horowitz & McConnell 2002，45 项研究），全样本几何均值
约 3.28（Tunçel & Hammitt 2014，76 项研究）。这就是"我觉得更好"自欺的
经济学根源，所以差异化必须可量化。

证据强度标注：Kano / Ulwick 属产品研究工具而非因果科学，
应作启发式权重而非真理。
"""

from __future__ import annotations

from dataclasses import dataclass

#: Ulwick 阈值
OPPORTUNITY_HIGH = 15.0     # ≥15 高吸引力，重点投入
OPPORTUNITY_PARTIAL = 10.0  # 10–15 部分市场有吸引力；<10 过度服务

#: Berger 阈值：多数用户会被显著影响
CS_PLUS_SIGNIFICANT = 0.5
CS_MINUS_SIGNIFICANT = -0.5

#: Kano 问卷可疑(Q)率超过此值说明题目设计有误，需重写
MAX_Q_RATE = 0.10


@dataclass(frozen=True)
class OpportunityScore:
    value: float
    band: str
    verdict: str
    explanation: str


def opportunity_score(importance: float, satisfaction: float) -> OpportunityScore:
    """Ulwick 机会分 = Importance + max(Importance − Satisfaction, 0)。

    量表 1–10，结果范围 0–20。``max()`` 保证非负，等效给 Importance 双倍权重。
    """
    for name, value in (("Importance", importance), ("Satisfaction", satisfaction)):
        if not 1.0 <= value <= 10.0:
            raise ValueError(f"{name} 必须在 1–10 量表内，收到 {value}")

    gap = max(importance - satisfaction, 0.0)
    value = importance + gap

    if value >= OPPORTUNITY_HIGH:
        band, verdict = "high", "高吸引力 —— 重点投入区"
    elif value >= OPPORTUNITY_PARTIAL:
        band, verdict = "partial", "部分市场有吸引力"
    else:
        band, verdict = "overserved", "过度服务 —— 放弃，或作为颠覆式创新的靶点"

    return OpportunityScore(
        value, band, verdict,
        f"机会分 = {importance:g} + max({importance:g} − {satisfaction:g}, 0) = {value:g}"
        f" → {verdict}",
    )


@dataclass(frozen=True)
class KanoResult:
    cs_plus: float
    cs_minus: float
    category: str
    is_screaming_point: bool
    q_rate: float
    questionnaire_valid: bool
    explanation: tuple[str, ...]


def kano_coefficients(
    attractive: int,      # A 兴奋型
    one_dimensional: int, # O 期望型
    must_be: int,         # M 必备型
    indifferent: int,     # I 无差异
    reverse: int = 0,     # R 反向
    questionable: int = 0,# Q 可疑
) -> KanoResult:
    """Berger Better-Worse 系数（Kano 量化）。

        CS+ = (A+O) / (A+O+M+I)        范围 0→1
        CS− = −(O+M) / (A+O+M+I)       范围 0→−1

    判读：
      CS+ 高 + CS− 强负 → 期望型
      CS+ 高 + CS− 近 0 → **兴奋型（尖叫点，爆品应锁定此象限）**
      CS+ 低 + CS− 强负 → 必备型（做好只是不被骂）
    """
    counts = (attractive, one_dimensional, must_be, indifferent, reverse, questionable)
    if any(n < 0 for n in counts):
        raise ValueError("各类计数不能为负")

    denominator = attractive + one_dimensional + must_be + indifferent
    if denominator == 0:
        raise ValueError("A+O+M+I 为 0 —— 无有效样本，应返回未知而非 0")

    cs_plus = (attractive + one_dimensional) / denominator
    cs_minus = -(one_dimensional + must_be) / denominator

    total = sum(counts)
    q_rate = questionable / total if total else 0.0
    valid = q_rate <= MAX_Q_RATE

    high_plus = cs_plus > CS_PLUS_SIGNIFICANT
    strong_minus = cs_minus < CS_MINUS_SIGNIFICANT

    if high_plus and not strong_minus:
        category, screaming = "attractive", True
    elif high_plus and strong_minus:
        category, screaming = "one_dimensional", False
    elif not high_plus and strong_minus:
        category, screaming = "must_be", False
    else:
        category, screaming = "indifferent", False

    labels = {
        "attractive": "兴奋型 —— 尖叫点，爆品应锁定此象限",
        "one_dimensional": "期望型 —— 做得越好满意度越高",
        "must_be": "必备型 —— 做好只是不被骂",
        "indifferent": "无差异 —— 用户不在乎，别投入",
    }
    lines = [
        f"CS+ = ({attractive}+{one_dimensional}) / {denominator} = {cs_plus:.4f}",
        f"CS− = −({one_dimensional}+{must_be}) / {denominator} = {cs_minus:.4f}",
        f"判定：{labels[category]}",
    ]
    if not valid:
        lines.append(
            f"⚠️ 可疑(Q)率 {q_rate:.1%} > {MAX_Q_RATE:.0%} —— 问卷题目设计有误，需重写后重测"
        )
    return KanoResult(cs_plus, cs_minus, category, screaming, q_rate, valid, tuple(lines))
