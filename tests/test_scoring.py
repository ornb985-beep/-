"""计算层单元测试 —— 公式对拍与边界行为。"""

from __future__ import annotations

import unittest

from oic.config import DEFAULT_CONFIG, SupplyParams, Weights
from oic.scoring import concentration as conc
from oic.scoring import differentiation as diff
from oic.scoring import dimensions as dim
from oic.scoring import supply as sup
from oic.scoring import switching as sw
from oic.scoring.aggregate import (
    aggregate_probabilities,
    inv_logit,
    logit,
    round_to_percent,
)
from oic.scoring.conformal import conformal_interval, mondrian_interval
from oic.scoring.engine import authenticity_coefficient
from oic.scoring.kelly import MAX_KELLY_FRACTION, position_size, wilson_lower_bound


class TestDimensions(unittest.TestCase):
    def test_hand_computed_scores(self):
        result = dim.score_dimensions(90, 80, 84, 70, 68.3, Weights())
        self.assertAlmostEqual(result.demand_strength, 87.0)          # 90×.5+84×.5
        self.assertAlmostEqual(result.feasibility, 80 * .4 + 70 * .4 + 68.3 * .2)
        self.assertAlmostEqual(result.total,
                               (87.0 + (80 * .4 + 70 * .4 + 68.3 * .2)) / 2)

    def test_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            dim.score_dimensions(101, 50, 50, 50, 50, Weights())
        with self.assertRaises(ValueError):
            dim.score_dimensions(-1, 50, 50, 50, 50, Weights())

    def test_resource_coefficient_never_learned(self):
        """resource 恒为 0.2 —— 加权重不该改变它的影响。"""
        heavy = Weights(c=40, o=40, d=40, e=40)
        a = dim.score_dimensions(80, 80, 80, 80, 100, Weights())
        b = dim.score_dimensions(80, 80, 80, 80, 100, heavy)
        # 资源贡献恒定 = 100 × 0.2
        self.assertAlmostEqual(a.feasibility - (80 * .4 + 80 * .4), 20.0)
        self.assertAlmostEqual(
            b.feasibility - (80 * .4 * 40 / 25 + 80 * .4 * 40 / 25), 20.0)

    def test_skill_coverage(self):
        self.assertAlmostEqual(dim.skill_coverage(("产品设计",)), 33.3)
        self.assertAlmostEqual(dim.skill_coverage(("产品", "后端", "增长")), 99.9)
        self.assertEqual(dim.skill_coverage(("会计",)), 0.0)

    def test_capital_tiers(self):
        self.assertEqual(dim.capital_score(50_000), 60)
        self.assertEqual(dim.capital_score(300_000), 70)
        self.assertEqual(dim.capital_score(1_000_000), 80)
        self.assertEqual(dim.capital_score(5_000_000), 90)


class TestPathCoefficient(unittest.TestCase):
    def test_c_grade_never_counts(self):
        """竞品自称「月销破万」不该骗到 1.2 系数 —— v3 已识别漏洞的修复。"""
        result = dim.path_coefficient((dim.GradedText("月销破万单", "C"),))
        self.assertEqual(result.coefficient, 0.8)
        self.assertIn("月销", result.rejected_c_grade_terms)

    def test_official_source_counts(self):
        result = dim.path_coefficient((dim.GradedText("GMV 破亿", "A"),))
        self.assertEqual(result.coefficient, 1.2)

    def test_intent_only(self):
        result = dim.path_coefficient((dim.GradedText("客单价接受度高", "B"),))
        self.assertEqual(result.coefficient, 1.0)

    def test_no_evidence(self):
        self.assertEqual(dim.path_coefficient(()).coefficient, 0.8)


class TestSupply(unittest.TestCase):
    def setUp(self):
        self.params = SupplyParams()

    def test_scissors_and_death_rate(self):
        self.assertEqual(sup.scissors_gap(45, 12), 33)
        self.assertAlmostEqual(sup.death_rate(40, 800), 0.05)

    def test_zero_active_companies_raises(self):
        """存续数为 0 时死亡率无定义，应报错而非返回 1.0。"""
        with self.assertRaises(ValueError):
            sup.death_rate(10, 0)

    def test_m_coefficient_bands(self):
        self.assertEqual(sup.m_coefficient(40, 0.01, self.params)[0], 1.3)
        self.assertEqual(sup.m_coefficient(20, 0.01, self.params)[0], 1.1)
        self.assertEqual(sup.m_coefficient(0, 0.01, self.params)[0], 1.0)
        self.assertEqual(sup.m_coefficient(-20, 0.01, self.params)[0], 0.7)

    def test_meatgrinder(self):
        coeff, flagged = sup.m_coefficient(-40, 0.30, self.params)
        self.assertEqual(coeff, 0.0)
        self.assertTrue(flagged)

    def test_meatgrinder_needs_both_conditions(self):
        """只有剪刀差极差但死亡率低 —— 不算绞肉机。"""
        coeff, flagged = sup.m_coefficient(-40, 0.02, self.params)
        self.assertFalse(flagged)
        self.assertEqual(coeff, 0.7)

    def test_risk_coefficient_floor(self):
        self.assertEqual(sup.risk_coefficient(0.9, self.params), 0.5)

    def test_sophistication_levels(self):
        self.assertEqual(sup.sophistication_level(5, 10, 0.02, self.params), "L1")
        self.assertEqual(sup.sophistication_level(30, 10, 0.02, self.params), "L2")
        self.assertEqual(sup.sophistication_level(100, 5, 0.02, self.params), "L3")
        self.assertEqual(sup.sophistication_level(500, 5, 0.02, self.params), "L4")
        self.assertEqual(sup.sophistication_level(500, -5, 0.30, self.params), "L5")


class TestSwitching(unittest.TestCase):
    def test_veto_on_nonpositive(self):
        result = sw.switching_potential(30, 25, 60, 55)
        self.assertTrue(result.vetoed)
        self.assertLessEqual(result.potential, 0)

    def test_healthy_potential(self):
        self.assertFalse(sw.switching_potential(72, 68, 30, 25).vetoed)

    def test_diy_is_strongest_signal(self):
        """「自己改了一下」是最高信号 —— 痛点真实到愿付出劳动。"""
        diy = sw.lexicon_intensity(("这个我自己改了一下才能用",), sw.TOLERANCE_LEXICON)
        settle = sw.lexicon_intensity(("习惯就好",), sw.TOLERANCE_LEXICON)
        self.assertGreater(diy, settle)

    def test_empty_corpus_gives_zero(self):
        self.assertEqual(sw.lexicon_intensity((), sw.TOLERANCE_LEXICON), 0.0)

    def test_repeated_terms_do_not_inflate(self):
        """同一条文本内重复同一个词不该刷高分数。"""
        once = sw.lexicon_intensity(("忍了",), sw.TOLERANCE_LEXICON)
        many = sw.lexicon_intensity(("忍了忍了忍了忍了",), sw.TOLERANCE_LEXICON)
        self.assertEqual(once, many)


class TestDifferentiation(unittest.TestCase):
    def test_ulwick_formula(self):
        result = diff.opportunity_score(10, 3)
        self.assertEqual(result.value, 17)
        self.assertEqual(result.band, "high")

    def test_overserved(self):
        self.assertEqual(diff.opportunity_score(4, 9).band, "overserved")

    def test_scale_enforced(self):
        with self.assertRaises(ValueError):
            diff.opportunity_score(11, 5)

    def test_kano_screaming_point(self):
        result = diff.kano_coefficients(attractive=60, one_dimensional=10,
                                        must_be=5, indifferent=25)
        self.assertTrue(result.is_screaming_point)
        self.assertEqual(result.category, "attractive")

    def test_kano_must_be(self):
        result = diff.kano_coefficients(attractive=5, one_dimensional=10,
                                        must_be=60, indifferent=25)
        self.assertEqual(result.category, "must_be")

    def test_kano_q_rate_invalidates(self):
        result = diff.kano_coefficients(attractive=30, one_dimensional=20,
                                        must_be=20, indifferent=20, questionable=15)
        self.assertFalse(result.questionnaire_valid)

    def test_kano_zero_denominator_raises(self):
        with self.assertRaises(ValueError):
            diff.kano_coefficients(0, 0, 0, 0)


class TestConcentration(unittest.TestCase):
    def test_hhi_monopoly(self):
        self.assertEqual(conc.hhi([100.0]), 10000.0)

    def test_hhi_bands(self):
        self.assertEqual(conc.analyze_concentration([5.0] * 20).band, "low")
        self.assertEqual(conc.analyze_concentration([50.0, 30.0, 20.0]).band, "high")

    def test_shares_over_100_rejected(self):
        with self.assertRaises(ValueError):
            conc.hhi([60.0, 60.0])

    def test_empty_shares_rejected(self):
        with self.assertRaises(ValueError):
            conc.hhi([])


class TestAggregate(unittest.TestCase):
    def test_logit_roundtrip(self):
        for p in (0.01, 0.3, 0.5, 0.77, 0.99):
            self.assertAlmostEqual(inv_logit(logit(p)), p, places=9)

    def test_extremization_pushes_away_from_half(self):
        """多个独立来源都说 0.7 时，聚合应比 0.7 更自信。"""
        result = aggregate_probabilities([0.7, 0.7, 0.7], extremize_a=1.5)
        self.assertGreater(result.probability, 0.7)
        self.assertAlmostEqual(result.naive_mean, 0.7)

    def test_a_equals_one_is_plain_logit_pooling(self):
        result = aggregate_probabilities([0.6, 0.8], extremize_a=1.0)
        self.assertAlmostEqual(result.probability, inv_logit((logit(.6) + logit(.8)) / 2))

    def test_disagreement_triggers_human_review(self):
        result = aggregate_probabilities([0.05, 0.95])
        self.assertTrue(result.requires_human_review)

    def test_agreement_does_not_trigger_review(self):
        self.assertFalse(aggregate_probabilities([0.70, 0.72, 0.68]).requires_human_review)

    def test_empty_input_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_probabilities([])

    def test_probability_granularity(self):
        """超预报 1% 的倍数，普通人报 10% 的倍数。"""
        self.assertEqual(round_to_percent(0.6342), 0.63)


class TestConformal(unittest.TestCase):
    def test_refuses_when_calibration_too_small(self):
        interval = conformal_interval(0.5, [0.1] * 5, alpha=0.10)
        self.assertFalse(interval.guaranteed)
        self.assertIn("校准未建立", interval.note)

    def test_produces_interval_with_enough_samples(self):
        residuals = [i / 100.0 for i in range(50)]
        interval = conformal_interval(0.5, residuals, alpha=0.10)
        self.assertTrue(interval.guaranteed)
        self.assertLessEqual(interval.lower, 0.5)
        self.assertGreaterEqual(interval.upper, 0.5)

    def test_smaller_alpha_gives_wider_interval(self):
        residuals = [i / 100.0 for i in range(60)]
        wide = conformal_interval(0.5, residuals, alpha=0.02)
        narrow = conformal_interval(0.5, residuals, alpha=0.20)
        self.assertGreaterEqual(wide.width, narrow.width)

    def test_empirical_coverage_holds(self):
        """用确定性构造的残差检验覆盖率确实达标。"""
        residuals = [((i * 37) % 100) / 100.0 for i in range(100)]
        interval = conformal_interval(0.5, residuals, alpha=0.10, clip_to_unit=False)
        covered = sum(1 for r in residuals if abs(r) <= (interval.upper - 0.5))
        self.assertGreaterEqual(covered / len(residuals), 0.90)

    def test_mondrian_falls_back_with_warning(self):
        by_category = {"a": [0.1] * 3, "b": [i / 100 for i in range(60)]}
        interval = mondrian_interval(0.5, "a", by_category, alpha=0.10)
        self.assertTrue(interval.guaranteed)
        self.assertIn("退回合并校准集", interval.note)

    def test_mondrian_can_refuse(self):
        by_category = {"a": [0.1] * 3}
        interval = mondrian_interval(0.5, "a", by_category, fallback_to_pooled=False)
        self.assertFalse(interval.guaranteed)

    def test_negative_residuals_rejected(self):
        with self.assertRaises(ValueError):
            conformal_interval(0.5, [-0.1] * 40)


class TestKelly(unittest.TestCase):
    def test_refuses_without_calibration(self):
        position = position_size(5, 10, 3.0, 100_000)
        self.assertTrue(position.refused)
        self.assertIsNone(position.fraction)

    def test_respects_quarter_kelly_cap(self):
        position = position_size(38, 40, 10.0, 100_000)
        self.assertLessEqual(position.fraction, MAX_KELLY_FRACTION)

    def test_uses_lower_bound_not_point_estimate(self):
        position = position_size(20, 40, 3.0, 100_000)
        self.assertLess(position.win_rate_lower, position.win_rate_point)

    def test_negative_edge_gives_zero(self):
        position = position_size(1, 40, 1.0, 100_000)
        self.assertEqual(position.fraction, 0.0)

    def test_wilson_bounds(self):
        self.assertGreaterEqual(wilson_lower_bound(0, 30), 0.0)
        self.assertLess(wilson_lower_bound(30, 30), 1.0)

    def test_more_data_allows_larger_position(self):
        small = position_size(20, 40, 3.0, 100_000)
        large = position_size(200, 400, 3.0, 100_000)
        self.assertLess(small.fraction, large.fraction)


class TestAuthenticity(unittest.TestCase):
    def test_floor_at_half(self):
        self.assertEqual(authenticity_coefficient(100), 0.5)

    def test_clean_data_unpenalised(self):
        self.assertEqual(authenticity_coefficient(0), 1.0)

    def test_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            authenticity_coefficient(120)


class TestAgentGate(unittest.TestCase):
    def test_unmeasured_baseline_blocks_multi_agent(self):
        """没测基线一律禁止扩多智能体 —— 铁律 2 的代码级执行。"""
        gate = DEFAULT_CONFIG.agent_gate
        self.assertIsNone(gate.baseline_accuracy)
        self.assertFalse(gate.multi_agent_allowed())
        self.assertIn("基线未测量", gate.reason())

    def test_high_baseline_blocks_expansion(self):
        from oic.config import AgentGate
        gate = AgentGate(baseline_accuracy=0.62, task_is_parallelizable=True)
        self.assertFalse(gate.multi_agent_allowed())

    def test_sequential_task_blocks_expansion(self):
        from oic.config import AgentGate
        gate = AgentGate(baseline_accuracy=0.30, task_is_parallelizable=False)
        self.assertFalse(gate.multi_agent_allowed())
        self.assertIn("顺序推理链", gate.reason())

    def test_low_baseline_parallel_task_allowed(self):
        from oic.config import AgentGate
        gate = AgentGate(baseline_accuracy=0.30, task_is_parallelizable=True)
        self.assertTrue(gate.multi_agent_allowed())


class TestConfigHonesty(unittest.TestCase):
    def test_uncalibrated_notice_present(self):
        """参数未校准时界面必须显示诚实标注。"""
        self.assertIsNotNone(DEFAULT_CONFIG.uncalibrated_notice())

    def test_detectors_default_off(self):
        detectors = DEFAULT_CONFIG.detectors
        self.assertFalse(detectors.benford_enabled)
        self.assertFalse(detectors.changepoint_enabled)
        self.assertFalse(detectors.template_cluster_enabled)

    def test_weight_cap_enforced(self):
        weights = Weights()
        for _ in range(20):
            weights = weights.bumped("e")
        self.assertLessEqual(weights.e, weights.cap)


if __name__ == "__main__":
    unittest.main()
