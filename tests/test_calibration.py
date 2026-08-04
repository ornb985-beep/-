"""校准层测试 —— Brier/Murphy、分层贝叶斯、代理双通道、eval 指标。"""

from __future__ import annotations

import math
import unittest

from oic.calibration import brier
from oic.calibration.hierarchical import (
    beta_quantile,
    betainc,
    partial_pool,
)
from oic.calibration.surrogate import (
    Channel,
    assert_channel,
    pearson,
    validate_surrogate,
)
from oic.eval.metrics import (
    cohen_kappa,
    evaluate_adversarial,
    ndcg_at_k,
    score_band_agreement,
    span_prf,
)
from oic.eval.run import evaluate


class TestBrier(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(brier.brier_score([1.0, 0.0], [1, 0]), 0.0)
        self.assertEqual(brier.brier_score([0.0, 1.0], [1, 0]), 1.0)
        self.assertAlmostEqual(
            brier.brier_score([0.8] * 5, [1, 1, 1, 1, 0]), (4 * 0.04 + 0.64) / 5)

    def test_murphy_identity_exact(self):
        forecasts = [i / 50.0 for i in range(50)]
        outcomes = [1 if (i * 7) % 10 < i / 5 else 0 for i in range(50)]
        d = brier.murphy_decomposition(forecasts, outcomes)
        self.assertAlmostEqual(d.identity_residual, 0.0, places=12)

    def test_binning_loss_is_nonnegative(self):
        forecasts = [i / 50.0 for i in range(50)]
        outcomes = [i % 2 for i in range(50)]
        d = brier.murphy_decomposition(forecasts, outcomes)
        self.assertGreaterEqual(d.binning_loss, -1e-12)

    def test_uncertainty_is_base_rate_benchmark(self):
        outcomes = [1] * 3 + [0] * 7
        self.assertAlmostEqual(brier.uncertainty(outcomes), 0.3 * 0.7)

    def test_small_sample_refuses_decomposition(self):
        report = brier.build_report([0.6] * 10, [1, 0, 1, 1, 0, 1, 0, 1, 1, 0])
        self.assertIsNone(report.decomposition)
        self.assertFalse(report.may_claim_effective)
        self.assertIn("校准未建立", report.status)

    def test_useful_system_passes_gate(self):
        forecasts = [0.9] * 20 + [0.1] * 20
        outcomes = [1] * 18 + [0] * 2 + [0] * 18 + [1] * 2
        self.assertTrue(brier.build_report(forecasts, outcomes).may_claim_effective)

    def test_uninformative_system_fails_gate(self):
        self.assertFalse(brier.build_report([0.5] * 40, [1, 0] * 20).may_claim_effective)

    def test_bss_positive_when_better_than_base_rate(self):
        forecasts = [0.9] * 20 + [0.1] * 20
        outcomes = [1] * 20 + [0] * 20
        self.assertGreater(brier.brier_skill_score(forecasts, outcomes), 0)

    def test_bss_undefined_on_constant_outcomes(self):
        with self.assertRaises(ValueError):
            brier.brier_skill_score([0.5, 0.5], [1, 1])

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            brier.brier_score([1.5], [1])
        with self.assertRaises(ValueError):
            brier.brier_score([0.5], [2])
        with self.assertRaises(ValueError):
            brier.brier_score([], [])

    def test_llm_ceiling_reference(self):
        """参照：最强 LLM Brier 0.122 ≈ 普通公众 0.121，超预 0.096。

        这条测试的意义是把基准钉在代码里 —— 系统若报出 0.05 这种
        远超超预的分数，几乎一定是数据泄漏而不是真的强。
        """
        superforecaster, public, llm = 0.096, 0.121, 0.122
        self.assertLess(superforecaster, public)
        self.assertAlmostEqual(llm, public, delta=0.01)


class TestHierarchical(unittest.TestCase):
    def setUp(self):
        self.data = {"露营": (3, 5), "咖啡": (20, 100), "香氛": (0, 0)}

    def test_small_sample_shrinks_more(self):
        camp = partial_pool(self.data, "露营")
        coffee = partial_pool(self.data, "咖啡")
        self.assertGreater(camp.shrinkage, coffee.shrinkage)

    def test_zero_sample_uses_global(self):
        scent = partial_pool(self.data, "香氛")
        self.assertAlmostEqual(scent.pooled_rate, scent.global_rate)
        self.assertTrue(scent.borrowed)

    def test_estimate_between_raw_and_global(self):
        camp = partial_pool(self.data, "露营")
        low, high = sorted((camp.raw_rate, camp.global_rate))
        self.assertGreaterEqual(camp.pooled_rate, low - 1e-9)
        self.assertLessEqual(camp.pooled_rate, high + 1e-9)

    def test_interval_narrows_with_data(self):
        camp = partial_pool(self.data, "露营")
        coffee = partial_pool(self.data, "咖啡")
        self.assertGreater(camp.upper - camp.lower, coffee.upper - coffee.lower)

    def test_no_data_anywhere_raises(self):
        with self.assertRaises(ValueError):
            partial_pool({}, "未知")

    def test_fallback_prior_accepted(self):
        estimate = partial_pool({}, "未知", fallback_global_rate=0.12)
        self.assertAlmostEqual(estimate.global_rate, 0.12)

    def test_beta_functions(self):
        self.assertAlmostEqual(betainc(1, 1, 0.3), 0.3, places=9)
        self.assertAlmostEqual(beta_quantile(1, 1, 0.5), 0.5, places=6)
        self.assertAlmostEqual(beta_quantile(2, 2, 0.5), 0.5, places=6)
        # Beta(2,1) 的 CDF 是 x²，故中位数 = √0.5
        self.assertAlmostEqual(beta_quantile(2, 1, 0.5), math.sqrt(0.5), places=6)

    def test_illegal_counts_rejected(self):
        with self.assertRaises(ValueError):
            partial_pool({"x": (10, 5)}, "x")


class TestSurrogate(unittest.TestCase):
    def test_strong_surrogate_promoted(self):
        n = 40
        values = [i / n for i in range(n)]
        outcomes = [1 if i >= n // 2 else 0 for i in range(n)]
        self.assertTrue(validate_surrogate(values, outcomes).may_write_calibration)

    def test_weak_surrogate_stays_in_fast_channel(self):
        n = 40
        values = [i / n for i in range(n)]
        outcomes = [i % 2 for i in range(n)]
        result = validate_surrogate(values, outcomes)
        self.assertFalse(result.may_write_calibration)
        self.assertEqual(result.allowed_channel, Channel.RANKING_ONLY)

    def test_insufficient_pairs_blocked(self):
        result = validate_surrogate([0.1, 0.2, 0.3], [0, 1, 1])
        self.assertEqual(result.reason, "insufficient_pairs")

    def test_channel_guard_raises(self):
        weak = validate_surrogate([i / 40 for i in range(40)],
                                  [i % 2 for i in range(40)])
        with self.assertRaises(PermissionError):
            assert_channel(weak, Channel.CALIBRATION)
        assert_channel(weak, Channel.RANKING_ONLY)   # 排序用途放行

    def test_pearson_known_value(self):
        self.assertAlmostEqual(pearson([1, 2, 3], [2, 4, 6]), 1.0)
        self.assertAlmostEqual(pearson([1, 2, 3], [6, 4, 2]), -1.0)

    def test_pearson_zero_variance_rejected(self):
        with self.assertRaises(ValueError):
            pearson([1, 1, 1], [1, 2, 3])


class TestEvalMetrics(unittest.TestCase):
    def test_span_prf_exact(self):
        result = span_prf([(0, 5), (10, 15)], [(0, 5), (10, 15)])
        self.assertEqual(result.f1, 1.0)

    def test_span_prf_partial_overlap(self):
        result = span_prf([(0, 10)], [(0, 6)], iou_threshold=0.5)
        self.assertEqual(result.true_positives, 1)

    def test_span_prf_below_threshold(self):
        result = span_prf([(0, 10)], [(9, 20)], iou_threshold=0.5)
        self.assertEqual(result.true_positives, 0)

    def test_span_prf_no_double_matching(self):
        """一个 gold span 不能被两个预测同时认领。"""
        result = span_prf([(0, 5), (0, 5)], [(0, 5)])
        self.assertEqual(result.true_positives, 1)
        self.assertEqual(result.false_positives, 1)

    def test_kappa_perfect_and_chance(self):
        self.assertAlmostEqual(cohen_kappa(["a", "b", "a"], ["a", "b", "a"]), 1.0)
        self.assertLess(cohen_kappa(["a", "b", "a", "b"], ["b", "a", "b", "a"]), 0.0)

    def test_kappa_undefined_when_no_variation(self):
        with self.assertRaises(ValueError):
            cohen_kappa(["a", "a"], ["a", "a"])

    def test_band_agreement(self):
        self.assertAlmostEqual(score_band_agreement([80, 60], [85, 90], tolerance=10),
                               0.5)

    def test_ndcg_perfect_ranking(self):
        relevance = {"a": 3.0, "b": 2.0, "c": 1.0}
        self.assertAlmostEqual(ndcg_at_k(["a", "b", "c"], relevance, k=3), 1.0)

    def test_ndcg_worst_ranking_lower(self):
        relevance = {"a": 3.0, "b": 2.0, "c": 1.0}
        self.assertLess(ndcg_at_k(["c", "b", "a"], relevance, k=3), 1.0)

    def test_ndcg_all_zero_relevance_raises(self):
        with self.assertRaises(ValueError):
            ndcg_at_k(["a"], {"a": 0.0})

    def test_adversarial_catch_rate(self):
        result = evaluate_adversarial([("fake-gmv", True), ("template-review", False)])
        self.assertAlmostEqual(result.catch_rate, 0.5)
        self.assertIn("template-review", result.missed)


class TestEvalRunner(unittest.TestCase):
    def test_empty_golden_set_is_graceful(self):
        """golden 集为空时应优雅报告，不能让 CI 常红。"""
        report = evaluate([])
        self.assertFalse(report.established)
        self.assertEqual(report.gate_failures(), ())
        self.assertTrue(any("未建立" in line for line in report.lines()))

    def test_populated_golden_set(self):
        records = [
            {"opportunity_id": "G-001",
             "human": {"c": 82, "o": 70, "d": 88, "e": 75, "rank": 1},
             "machine": {"c": 80, "o": 74, "d": 85, "e": 72},
             "spans": {"predicted": [[10, 15]], "gold": [[10, 16]]}},
            {"opportunity_id": "G-002",
             "human": {"c": 50, "o": 45, "d": 40, "e": 55, "rank": 2},
             "machine": {"c": 52, "o": 48, "d": 44, "e": 51},
             "spans": {"predicted": [[0, 4]], "gold": [[0, 4]]}},
        ]
        report = evaluate(records)
        self.assertTrue(report.established)
        self.assertEqual(report.n, 2)
        self.assertIsNotNone(report.span_f1)
        self.assertIsNotNone(report.ndcg)

    def test_gate_flags_poor_performance(self):
        records = [
            {"opportunity_id": "G-001",
             "human": {"c": 90, "o": 90, "d": 90, "e": 90},
             "machine": {"c": 10, "o": 10, "d": 10, "e": 10}},
        ]
        report = evaluate(records)
        self.assertTrue(report.gate_failures())


if __name__ == "__main__":
    unittest.main()
