"""切换势能 —— JTBD 四力模型。

    切换势能 = (推力 + 拉力) − (焦虑 + 惯性)

为什么必须有：原 C/O/D/E 只测推力和拉力，完全不测焦虑和惯性，
导致系统持续推荐"痛点真实、市场够大、但用户就是不换"的商机。
这类项目最坑 —— 数据全对，就是卖不动。

势能 ≤ 0 → 无论分多高，一票否决，降级为"观察"。
"""

from __future__ import annotations

from dataclasses import dataclass

#: Moesta 的经验：10 个精选近期购买者访谈即可揭示 3–5 种购买模式、覆盖 90% 市场。
#: 所以实验模块的访谈数定为 10，不是 100。
RECOMMENDED_INTERVIEWS = 10

#: 忍受词典 —— 真正的深层需求不在差评里，在"将就的表达"里。
#: 优先级：忍受词 > 差评。差评是愤怒（有人管了），忍受是绝望（没人管）。
TOLERANCE_LEXICON: tuple[tuple[str, float], ...] = (
    ("自己改了", 1.0),      # 最高信号：用户已动手 DIY，痛点真实到愿付出劳动
    ("自己改装", 1.0),
    ("自己动手", 0.9),
    ("凑合能用", 0.7),
    ("凑合用", 0.7),
    ("忍了", 0.7),
    ("没办法只能", 0.7),
    ("已经是最好的", 0.6),
    ("将就", 0.6),
    ("习惯就好", 0.5),
)

#: 焦虑词 —— 差评/问大家里的"怕买错""不敢换"就是原始语料。
ANXIETY_LEXICON: tuple[tuple[str, float], ...] = (
    ("怕买错", 1.0),
    ("不敢买", 0.9),
    ("担心", 0.6),
    ("会不会", 0.5),
    ("能退吗", 0.7),
    ("踩雷", 0.8),
)

#: 惯性词 —— 沉没成本与使用习惯深度。
INERTIA_LEXICON: tuple[tuple[str, float], ...] = (
    ("用回原来", 1.0),
    ("还是原来的好", 0.9),
    ("用惯了", 0.8),
    ("懒得换", 0.8),
    ("已经买了", 0.6),
)


@dataclass(frozen=True)
class SwitchingPotential:
    push: float
    pull: float
    anxiety: float
    inertia: float
    potential: float
    vetoed: bool
    explanation: tuple[str, ...]


def lexicon_intensity(texts: tuple[str, ...], lexicon: tuple[tuple[str, float], ...]) -> float:
    """按词典计算 0–100 的强度分。

    命中权重求和后除以文本条数并缩放；同一条文本内同一词只计一次，
    避免复读机式文本刷高分数。
    """
    if not texts:
        return 0.0
    total = 0.0
    for text in texts:
        best = 0.0
        for term, weight in lexicon:
            if term in text:
                best = max(best, weight)
        total += best
    return min(total / len(texts) * 100.0, 100.0)


def switching_potential(
    push: float, pull: float, anxiety: float, inertia: float
) -> SwitchingPotential:
    """计算切换势能并给出一票否决判定。

    Bob Moesta 四力模型的核心不等式：推力+拉力 > 焦虑+惯性 时切换才发生。
    """
    for name, value in (("推力", push), ("拉力", pull),
                        ("焦虑", anxiety), ("惯性", inertia)):
        if not 0.0 <= value <= 100.0:
            raise ValueError(f"{name} 必须在 0–100 之间，收到 {value}")

    potential = (push + pull) - (anxiety + inertia)
    vetoed = potential <= 0.0

    lines = [
        f"切换势能 = ({push:g} + {pull:g}) − ({anxiety:g} + {inertia:g}) = {potential:g}",
    ]
    if vetoed:
        lines.append(
            "🔴 切换势能 ≤ 0 —— 一票否决，降级为「观察」。"
            "痛点可能真实，但用户不会换：焦虑与惯性压过了推力与拉力。"
        )
    return SwitchingPotential(push, pull, anxiety, inertia, potential, vetoed, tuple(lines))


def potential_from_texts(
    complaint_texts: tuple[str, ...],
    gap_score: float,
    question_texts: tuple[str, ...],
    resale_texts: tuple[str, ...],
) -> SwitchingPotential:
    """从原始语料直接算四力 —— 焦虑和惯性可以从数据读出来。

    * 推力 ← 抱怨/忍受词密度（忍受词典就是这个）
    * 拉力 ← 现有方案的具体缺口（≈ O 维度）
    * 焦虑 ← "问大家"里的顾虑（购买决策前的信任缺口）
    * 惯性 ← 转卖描述里的"还是用回原来那个了"
    """
    push = lexicon_intensity(complaint_texts, TOLERANCE_LEXICON)
    anxiety = lexicon_intensity(question_texts, ANXIETY_LEXICON)
    inertia = lexicon_intensity(resale_texts, INERTIA_LEXICON)
    return switching_potential(push, gap_score, anxiety, inertia)
