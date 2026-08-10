"""注意力信号的结构约束 —— 热榜不能单独支撑高分。

## 依据（重要：不是拟合出来的）

第一性原理写的是：**商机 = 需求增速 > 供给增速的交集**。

交集需要两个集合。热榜、RSS、社零数据全部只测需求侧注意力，
**它们回答不了"供给增速是多少"**。所以：

    只有需求侧证据的商机 → 剪刀差无定义 → 不得进入高分档

这是从公式定义本身推出来的约束，不是从数据拟合出来的参数。
即使样本量为零，这条也成立。

## 一条不能用作依据的观察

回测里 2022 年增速最高的两个品类（露营 +52%、剧本杀 +45%）到 2025 全灭，
已降温的盲盒（+2.8%）反而是唯一双标签全正。

**但 n=7、ρ=−0.289、精确 p=0.629 —— 统计上不显著。**
把它写成"热度越高越该扣分"的惩罚项，就是在 n=7 上拟合噪声，
正是 `oic/stats/overfit.py` 警告的那件事。

所以本模块**只做结构性拦截，不做热度惩罚**：
不因为"热"而扣分，只因为"缺供给侧证据"而封顶。
两者的区别是：前者是猜测，后者是定义。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

#: 只测需求侧注意力的源类型 —— 它们无法单独支撑剪刀差
ATTENTION_ONLY_SOURCES = frozenset({
    "weibo_hot", "zhihu_hot", "baidu_hot", "toutiao_hot", "douyin_hot",
    "rss_36kr", "rss_huxiu", "rss_iyiou", "stats_gov",
})

#: 能提供供给侧证据的源
SUPPLY_SIDE_SOURCES = frozenset({
    "gsxt_gov", "qcc_open", "sec_edgar", "cninfo", "trademark_gov",
})

#: 缺供给侧证据时，排序分的封顶比例。
#: 不是惩罚系数 —— 是"未验证交集"的置信上限。
NO_SUPPLY_EVIDENCE_CAP = 0.6


@dataclass(frozen=True)
class AttentionProfile:
    n_attention_sources: int
    n_supply_sources: int
    has_supply_evidence: bool
    scissors_computable: bool
    cap_multiplier: float
    explanation: tuple[str, ...]

    @property
    def attention_only(self) -> bool:
        return self.n_attention_sources > 0 and not self.has_supply_evidence


def profile_sources(source_keys: Sequence[str]) -> AttentionProfile:
    """判断证据结构是否足以计算剪刀差。

    ``source_keys`` 是该商机全部证据的来源 key。
    """
    unique = sorted(set(source_keys))
    attention = [k for k in unique if k in ATTENTION_ONLY_SOURCES]
    supply = [k for k in unique if k in SUPPLY_SIDE_SOURCES]

    has_supply = bool(supply)
    lines: list[str] = [
        f"证据来源：{len(attention)} 个需求侧注意力源，{len(supply)} 个供给侧源",
    ]

    if has_supply:
        lines.append("剪刀差可计算 —— 两侧证据齐备")
        cap = 1.0
    else:
        cap = NO_SUPPLY_EVIDENCE_CAP
        lines.extend([
            f"⚠️ **无供给侧证据，剪刀差无定义** —— 排序分封顶至 {cap:.0%}",
            "这不是因为「热度高要扣分」，而是因为「需求 > 供给的交集」"
            "缺了一半，交集根本没算出来。",
            "解法不是调分，是补数据：企业注册/注销、门店数、"
            "同业公司数、招股书的行业竞争格局章节。",
        ])
        if attention:
            lines.append(
                "注意：热榜与媒体 RSS 天然放大**已经很热**的东西。"
                "它们擅长告诉你「现在什么火」，不擅长告诉你「窗口还开着吗」。"
            )

    return AttentionProfile(
        n_attention_sources=len(attention),
        n_supply_sources=len(supply),
        has_supply_evidence=has_supply,
        scissors_computable=has_supply,
        cap_multiplier=cap,
        explanation=tuple(lines),
    )


def apply_cap(rank_score: float, profile: AttentionProfile) -> tuple[float, str]:
    """把封顶应用到排序分。返回 ``(封顶后的分, 说明)``。"""
    if rank_score < 0:
        raise ValueError("排序分不能为负")
    if profile.cap_multiplier >= 1.0:
        return rank_score, "证据结构完整，排序分不封顶"
    capped = rank_score * profile.cap_multiplier
    return capped, (
        f"排序分 {rank_score:.2f} × {profile.cap_multiplier:g}（缺供给侧证据）"
        f" = {capped:.2f}"
    )
