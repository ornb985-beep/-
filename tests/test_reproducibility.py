"""G0 门：可复现性硬断言。

这不是普通单元测试 —— 它是架构正确性的自动检测器。
包含一个**反向测试**：向计算层注入非确定性后，断言 verify_scores 必须失败。
"""

from __future__ import annotations

import unittest
from unittest import mock

from oic.scoring import engine
from oic.scoring.engine import (
    ReproducibilityError,
    compute_all_scores,
    rank_opportunities,
    verify_scores,
)
from tests.fixtures import healthy_opportunity, meatgrinder_opportunity


class TestReproducibility(unittest.TestCase):
    def test_verify_scores_passes(self):
        result = verify_scores(healthy_opportunity())
        self.assertGreater(result.rank_score, 0.0)

    def test_repeated_runs_byte_identical(self):
        opportunity = healthy_opportunity()
        runs = [compute_all_scores(opportunity).to_canonical_json() for _ in range(20)]
        self.assertEqual(len(set(runs)), 1, "20 次运行必须产生完全相同的结果")

    def test_ranking_is_stable(self):
        opportunities = [
            healthy_opportunity(opportunity_id=f"OPP-{i:03d}", c=70.0 + i)
            for i in range(10)
        ]
        first = [r.opportunity_id for r in rank_opportunities(opportunities)]
        shuffled = list(reversed(opportunities))
        second = [r.opportunity_id for r in rank_opportunities(shuffled)]
        self.assertEqual(first, second, "输入顺序不得影响排序结果")

    def test_ties_broken_deterministically(self):
        a = healthy_opportunity(opportunity_id="OPP-B")
        b = healthy_opportunity(opportunity_id="OPP-A")
        ranked = [r.opportunity_id for r in rank_opportunities([a, b])]
        self.assertEqual(ranked, ["OPP-A", "OPP-B"], "并列时按 id 升序，保证确定性")

    # --- 反向测试：注入非确定性后必须失败 -------------------------------
    def test_injecting_nondeterminism_makes_verify_fail(self):
        """把一个非确定性函数塞进计算层，verify_scores 必须抓到它。

        这验证的是断言本身有效 —— 一个永远通过的断言等于没有断言。
        """
        counter = {"n": 0}
        real = engine.authenticity_coefficient

        def drifting(fake_review_score, k=1.0):
            counter["n"] += 1
            return real(fake_review_score, k) + counter["n"] * 1e-9

        with mock.patch.object(engine, "authenticity_coefficient", drifting):
            with self.assertRaises(ReproducibilityError):
                verify_scores(healthy_opportunity())

    def test_engine_module_imports_no_nondeterministic_stdlib(self):
        """计算层不得依赖 random / time / datetime —— 静态检查。"""
        import ast
        import pathlib

        scoring_dir = pathlib.Path(engine.__file__).parent
        forbidden = {"random", "time", "datetime", "secrets", "uuid"}
        offenders = []
        for path in sorted(scoring_dir.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in forbidden:
                            offenders.append(f"{path.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.split(".")[0] in forbidden:
                        offenders.append(f"{path.name}: from {node.module}")
        self.assertEqual(offenders, [], f"计算层引入了非确定性依赖: {offenders}")


class TestRedlineZeroing(unittest.TestCase):
    def test_meatgrinder_zeroes_rank_score(self):
        result = verify_scores(meatgrinder_opportunity())
        self.assertEqual(result.rank_score, 0.0)
        self.assertIn("R2", result.redlines)

    def test_redline_cannot_be_offset_by_high_scores(self):
        """满分商机 + 一条红线 = 0。红线不可被高分抵消。"""
        opportunity = healthy_opportunity(
            opportunity_id="OPP-PERFECT",
            c=100.0, o=100.0, d=100.0, e=100.0,
            compliance_flags=("regulatory",),
        )
        result = verify_scores(opportunity)
        self.assertEqual(result.rank_score, 0.0)
        self.assertFalse(result.passed_redlines)

    def test_unknown_compliance_flag_rejected(self):
        opportunity = healthy_opportunity(compliance_flags=("made_up_category",))
        with self.assertRaises(ValueError):
            compute_all_scores(opportunity)


if __name__ == "__main__":
    unittest.main()
