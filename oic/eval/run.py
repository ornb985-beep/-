"""Eval 运行器与 CI 门禁。

    python -m oic.eval.run --golden data/golden.seed.jsonl
    python -m oic.eval.run --golden data/golden.seed.jsonl --gate

``--gate`` 用于 CI：任一指标低于基线即以非零码退出，阻断合并。

golden 集每行一条 JSON::

    {"opportunity_id": "G-001",
     "human": {"c": 82, "o": 70, "d": 88, "e": 75, "rank": 1},
     "machine": {"c": 80, "o": 74, "d": 85, "e": 72},
     "spans": {"predicted": [[10,15]], "gold": [[10,16]]},
     "category": "户外露营"}

集合为空时**优雅报告"golden set 未建立"并返回 0** ——
因为在 Wave 0 手工验证跑完之前，这是诚实的状态，不该让 CI 常红。
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from oic.eval.metrics import (
    cohen_kappa,
    ndcg_at_k,
    score_band_agreement,
    span_prf,
)

#: CI 门禁基线（PRIOR，随 golden 集建立后调整）
GATE_MIN_SPAN_F1 = 0.70
GATE_MIN_BAND_AGREEMENT = 0.60
GATE_MIN_NDCG = 0.70


@dataclass(frozen=True)
class EvalReport:
    n: int
    span_f1: float | None
    band_agreement: float | None
    kappa: float | None
    ndcg: float | None
    established: bool
    notes: tuple[str, ...]

    def lines(self) -> tuple[str, ...]:
        if not self.established:
            return self.notes
        out = [f"golden 集样本数：{self.n}"]
        if self.span_f1 is not None:
            out.append(f"抽取级 span F1 = {self.span_f1:.3f}"
                       f"（门禁 ≥{GATE_MIN_SPAN_F1}）")
        if self.band_agreement is not None:
            out.append(f"判断级 容差一致率 = {self.band_agreement:.3f}"
                       f"（门禁 ≥{GATE_MIN_BAND_AGREEMENT}）")
        if self.kappa is not None:
            out.append(f"判断级 Cohen's κ = {self.kappa:.3f}"
                       "（参照：细粒度标注任务 κ≈0.27 已是常态，别期待 0.8）")
        if self.ndcg is not None:
            out.append(f"系统级 NDCG@10 = {self.ndcg:.3f}"
                       f"（门禁 ≥{GATE_MIN_NDCG}）")
        out.extend(self.notes)
        return tuple(out)

    def gate_failures(self) -> tuple[str, ...]:
        if not self.established:
            return ()
        failures: list[str] = []
        if self.span_f1 is not None and self.span_f1 < GATE_MIN_SPAN_F1:
            failures.append(f"span F1 {self.span_f1:.3f} < {GATE_MIN_SPAN_F1}")
        if (self.band_agreement is not None
                and self.band_agreement < GATE_MIN_BAND_AGREEMENT):
            failures.append(
                f"容差一致率 {self.band_agreement:.3f} < {GATE_MIN_BAND_AGREEMENT}")
        if self.ndcg is not None and self.ndcg < GATE_MIN_NDCG:
            failures.append(f"NDCG@10 {self.ndcg:.3f} < {GATE_MIN_NDCG}")
        return tuple(failures)


def _band(score: float) -> str:
    if score >= 80:
        return "high"
    if score >= 65:
        return "mid"
    return "low"


def evaluate(records: list[dict]) -> EvalReport:
    if not records:
        return EvalReport(
            0, None, None, None, None, False,
            ("golden set 未建立（0 条）。",
             "这不是失败：Wave 0 的手工品类验证结果就是第一批标注数据，",
             "跑完后写进 data/golden.seed.jsonl 即可让本报告开始工作。"),
        )

    notes: list[str] = []
    dims = ("c", "o", "d", "e")

    # --- 抽取级 ---
    all_pred: list[tuple[int, int]] = []
    all_gold: list[tuple[int, int]] = []
    for record in records:
        spans = record.get("spans") or {}
        all_pred.extend(tuple(s) for s in spans.get("predicted", []))
        all_gold.extend(tuple(s) for s in spans.get("gold", []))
    span_f1 = span_prf(all_pred, all_gold).f1 if all_gold else None
    if all_gold is not None and not all_gold:
        notes.append("（无 span 标注，跳过抽取级评测）")

    # --- 判断级 ---
    predicted_scores: list[float] = []
    gold_scores: list[float] = []
    for record in records:
        human = record.get("human") or {}
        machine = record.get("machine") or {}
        for dim in dims:
            if dim in human and dim in machine:
                gold_scores.append(float(human[dim]))
                predicted_scores.append(float(machine[dim]))

    band_agreement = (score_band_agreement(predicted_scores, gold_scores)
                      if gold_scores else None)
    kappa: float | None = None
    if gold_scores:
        try:
            kappa = cohen_kappa([_band(s) for s in predicted_scores],
                                [_band(s) for s in gold_scores])
        except ValueError as exc:
            notes.append(f"（κ 未计算：{exc}）")

    # --- 系统级 ---
    ndcg: float | None = None
    ranked = [r for r in records if (r.get("human") or {}).get("rank") is not None]
    if len(ranked) >= 2:
        n = len(ranked)
        relevance = {
            r["opportunity_id"]: float(n - int(r["human"]["rank"]) + 1) for r in ranked
        }
        # 机器排序：用四维均值代替排序分（golden 集不含完整输入）
        def machine_score(record: dict) -> float:
            machine = record.get("machine") or {}
            values = [float(machine[d]) for d in dims if d in machine]
            return sum(values) / len(values) if values else 0.0

        order = sorted(ranked, key=lambda r: (-machine_score(r), r["opportunity_id"]))
        try:
            ndcg = ndcg_at_k([r["opportunity_id"] for r in order], relevance, k=10)
        except ValueError as exc:
            notes.append(f"（NDCG 未计算：{exc}）")
    else:
        notes.append("（人工排序标注 <2 条，跳过系统级评测）")

    return EvalReport(len(records), span_f1, band_agreement, kappa, ndcg, True,
                      tuple(notes))


def load(path: Path) -> list[dict]:
    records: list[dict] = []
    if not path.exists():
        return records
    with path.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno} JSON 解析失败: {exc}") from exc
    return records


def main(argv: list[str]) -> int:
    if "--golden" not in argv:
        print(__doc__)
        return 0
    idx = argv.index("--golden")
    if idx + 1 >= len(argv):
        print("用法：--golden <path>", file=sys.stderr)
        return 2

    path = Path(argv[idx + 1])
    records = load(path)
    report = evaluate(records)

    print(f"Eval 报告 —— {path}")
    for line in report.lines():
        print(" ", line)

    if "--gate" in argv:
        failures = report.gate_failures()
        if failures:
            print("\n⛔ CI 门禁未通过：", file=sys.stderr)
            for failure in failures:
                print(f"  - {failure}", file=sys.stderr)
            return 1
        print("\n✅ CI 门禁通过"
              if report.established else "\n⚪ golden set 未建立，门禁跳过")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
