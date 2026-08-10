"""三级评测指标，纯标准库实现。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


# ---------------------------------------------------------------------------
# 抽取级：span P/R/F1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PRF:
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int

    def line(self) -> str:
        return (f"P={self.precision:.3f} R={self.recall:.3f} F1={self.f1:.3f} "
                f"(TP={self.true_positives} FP={self.false_positives} "
                f"FN={self.false_negatives})")


def span_prf(
    predicted: Sequence[tuple[int, int]],
    gold: Sequence[tuple[int, int]],
    iou_threshold: float = 0.5,
) -> PRF:
    """按 IoU 匹配的 span 级 P/R/F1。

    ``iou_threshold=1.0`` 即要求精确匹配。默认 0.5 允许边界略有出入 ——
    因为标注者对"哪几个字算证据"的判断本身就有分歧。
    """
    if not 0.0 < iou_threshold <= 1.0:
        raise ValueError("iou_threshold 必须在 (0,1] 之间")

    def iou(a: tuple[int, int], b: tuple[int, int]) -> float:
        inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
        union = max(a[1], b[1]) - min(a[0], b[0])
        return inter / union if union > 0 else 0.0

    unmatched_gold = list(gold)
    tp = 0
    for span in predicted:
        best_idx, best_iou = -1, 0.0
        for idx, gold_span in enumerate(unmatched_gold):
            score = iou(span, gold_span)
            if score > best_iou:
                best_idx, best_iou = idx, score
        if best_idx >= 0 and best_iou >= iou_threshold:
            tp += 1
            unmatched_gold.pop(best_idx)

    fp = len(predicted) - tp
    fn = len(unmatched_gold)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)
    return PRF(precision, recall, f1, tp, fp, fn)


# ---------------------------------------------------------------------------
# 判断级：Cohen's κ
# ---------------------------------------------------------------------------


def cohen_kappa(rater_a: Sequence[str], rater_b: Sequence[str]) -> float:
    """Cohen's κ —— 扣除偶然一致后的一致率。

    参照物：GoEmotions 的 27 类情绪标注，标注者间 κ 仅约 0.27。
    所以对细粒度判断任务不要期待 κ>0.8；0.4–0.6 已算可用。
    """
    n = len(rater_a)
    if n != len(rater_b):
        raise ValueError("两位标注者的条数必须一致")
    if n == 0:
        raise ValueError("样本为空")

    labels = sorted(set(rater_a) | set(rater_b))
    observed = sum(1 for a, b in zip(rater_a, rater_b) if a == b) / n

    expected = 0.0
    for label in labels:
        pa = sum(1 for a in rater_a if a == label) / n
        pb = sum(1 for b in rater_b if b == label) / n
        expected += pa * pb

    if expected >= 1.0:
        # 两人都只用了同一个标签 —— κ 无定义
        raise ValueError("偶然一致率为 1 —— κ 无定义（标签无变化）")
    return (observed - expected) / (1.0 - expected)


def score_band_agreement(
    predicted: Sequence[float], gold: Sequence[float], tolerance: float = 10.0
) -> float:
    """0–100 分的容差一致率 —— 比精确相等更贴合打分任务。"""
    if len(predicted) != len(gold):
        raise ValueError("条数必须一致")
    if not predicted:
        raise ValueError("样本为空")
    hits = sum(1 for p, g in zip(predicted, gold) if abs(p - g) <= tolerance)
    return hits / len(predicted)


# ---------------------------------------------------------------------------
# 系统级：NDCG@k
# ---------------------------------------------------------------------------


def dcg(relevances: Sequence[float], k: int) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances[:k]))


def ndcg_at_k(
    ranked_ids: Sequence[str],
    relevance: dict[str, float],
    k: int = 10,
) -> float:
    """NDCG@k —— 系统排序与人工理想排序的接近程度。

    ``relevance`` 是人工给的相关度（如人工排序位次转成的增益）。
    """
    if k <= 0:
        raise ValueError("k 必须为正")
    if not ranked_ids:
        raise ValueError("排序结果为空")

    actual = [relevance.get(item_id, 0.0) for item_id in ranked_ids]
    ideal = sorted(relevance.values(), reverse=True)

    idcg = dcg(ideal, k)
    if idcg == 0.0:
        raise ValueError("理想 DCG 为 0 —— 所有条目相关度都是 0，NDCG 无定义")
    return dcg(actual, k) / idcg


# ---------------------------------------------------------------------------
# 对抗集判定
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdversarialResult:
    total: int
    caught: int
    missed: tuple[str, ...]

    @property
    def catch_rate(self) -> float:
        return self.caught / self.total if self.total else 0.0

    def line(self) -> str:
        return (f"对抗集拦截率 {self.catch_rate:.1%}（{self.caught}/{self.total}）"
                + (f"，漏网：{'、'.join(self.missed)}" if self.missed else ""))


def evaluate_adversarial(
    cases: Sequence[tuple[str, bool]],
) -> AdversarialResult:
    """``cases`` 为 (用例 id, 是否被系统识破)。"""
    caught = sum(1 for _, ok in cases if ok)
    missed = tuple(case_id for case_id, ok in cases if not ok)
    return AdversarialResult(len(cases), caught, missed)
