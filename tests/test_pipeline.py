"""变化率引擎与成本硬顶的测试。"""

from __future__ import annotations

import unittest

from oic.pipeline.budget import (
    BudgetExhausted,
    BudgetMisconfigured,
    DailyCaps,
    FunnelStage,
    Ledger,
    Resource,
    assert_funnel_feasible,
    honest_count,
    select_for_escalation,
)
from oic.research.velocity import (
    Shape,
    SnapshotSeries,
    Snapshot,
    Trend,
    classify,
    velocity_score,
)


def series(values, start_day=1):
    return [Snapshot("f1", f"2026-08-{start_day + i:02d}", v)
            for i, v in enumerate(values)]


class TestVelocityClassify(unittest.TestCase):
    def test_first_appearance_is_new(self):
        r = classify(series([100.0]))
        self.assertEqual(r.trend, Trend.NEW)
        self.assertEqual(r.shape, Shape.UNKNOWN)
        self.assertIsNone(r.change_pct)

    def test_up_and_down(self):
        self.assertEqual(classify(series([100.0, 130.0])).trend, Trend.UP)
        self.assertEqual(classify(series([100.0, 70.0])).trend, Trend.DOWN)

    def test_small_change_is_flat_not_trend(self):
        """1% 的变动是噪声，不该读成趋势。"""
        self.assertEqual(classify(series([100.0, 101.0])).trend, Trend.FLAT)

    def test_accelerating(self):
        r = classify(series([100.0, 110.0, 140.0]))   # +10% → +27%
        self.assertEqual(r.trend, Trend.UP)
        self.assertEqual(r.shape, Shape.ACCELERATING)

    def test_decelerating(self):
        r = classify(series([100.0, 150.0, 165.0]))   # +50% → +10%
        self.assertEqual(r.shape, Shape.DECELERATING)

    def test_reversing(self):
        r = classify(series([100.0, 140.0, 90.0]))    # +40% → -36%
        self.assertEqual(r.shape, Shape.REVERSING)

    def test_steady(self):
        r = classify(series([100.0, 110.0, 121.0]))   # +10% → +10%
        self.assertEqual(r.shape, Shape.STEADY)

    def test_two_points_have_no_second_order(self):
        """只有两期就说不出加速减速 —— 不猜。"""
        r = classify(series([100.0, 130.0]))
        self.assertEqual(r.shape, Shape.UNKNOWN)
        self.assertFalse(r.has_second_order)

    def test_zero_base_refuses_change_rate(self):
        """基期为 0 时环比无定义，必须拒绝而不是除零或返回 0。"""
        r = classify(series([0.0, 50.0]))
        self.assertIsNone(r.change_pct)
        self.assertIn("无定义", "".join(r.explanation))

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            classify([])

    def test_mixed_fingerprints_rejected(self):
        with self.assertRaises(ValueError):
            classify([Snapshot("a", "2026-08-01", 1.0),
                      Snapshot("b", "2026-08-02", 2.0)])

    def test_same_day_last_write_wins(self):
        snaps = [Snapshot("f1", "2026-08-01", 1.0),
                 Snapshot("f1", "2026-08-01", 5.0),
                 Snapshot("f1", "2026-08-02", 10.0)]
        self.assertEqual(classify(snaps).n_points, 2)

    def test_out_of_order_input_is_sorted(self):
        forward = classify(series([100.0, 130.0, 170.0]))
        shuffled = classify(list(reversed(series([100.0, 130.0, 170.0]))))
        self.assertEqual(forward.change_pct, shuffled.change_pct)
        self.assertEqual(forward.shape, shuffled.shape)


class TestVelocityScore(unittest.TestCase):
    def test_rising_beats_falling(self):
        up = velocity_score(classify(series([100.0, 140.0])))
        down = velocity_score(classify(series([100.0, 60.0])))
        self.assertGreater(up.score, down.score)

    def test_static_value_scores_mid_not_high(self):
        """静态绝对值天然低分 —— 「它有多大」不回答「它在不在涨」。"""
        static = velocity_score(classify(series([999999.0])))
        rising = velocity_score(classify(series([100.0, 150.0])))
        self.assertLess(static.score, rising.score)

    def test_outlier_change_is_saturated(self):
        """+900% 不该压过所有正常信号。"""
        big = velocity_score(classify(series([100.0, 1000.0])))
        normal = velocity_score(classify(series([100.0, 160.0])))
        self.assertLess(big.score - normal.score, 5.0)

    def test_score_bounded(self):
        for vals in ([100.0], [100.0, 1e9], [1e9, 1.0], [100.0, 110.0, 121.0]):
            s = velocity_score(classify(series(vals)))
            self.assertGreaterEqual(s.score, 0.0)
            self.assertLessEqual(s.score, 100.0)

    def test_score_declares_itself_uncalibrated(self):
        s = velocity_score(classify(series([100.0, 150.0])))
        self.assertFalse(s.calibrated)
        self.assertIn("PRIOR", "".join(s.explanation))

    def test_reversal_penalised_versus_acceleration(self):
        accel = velocity_score(classify(series([100.0, 110.0, 140.0])))
        rev = velocity_score(classify(series([100.0, 140.0, 145.0])))
        self.assertGreater(accel.score, rev.score - 100)  # 形态项确有影响
        self.assertNotEqual(accel.reading.shape, rev.reading.shape)


class TestSnapshotSeries(unittest.TestCase):
    def test_rank_is_deterministic(self):
        s = SnapshotSeries()
        for fp, vals in (("a", [10, 12]), ("b", [10, 20]), ("c", [10, 5])):
            for i, v in enumerate(vals):
                s.record(fp, f"2026-08-{i+1:02d}", float(v))
        first = [x.fingerprint for x in s.rank()]
        second = [x.fingerprint for x in s.rank()]
        self.assertEqual(first, second)
        self.assertEqual(first[0], "b")     # 涨得最多的排第一

    def test_missing_fingerprint_raises(self):
        with self.assertRaises(KeyError):
            SnapshotSeries().read("nope")


class TestBudgetCaps(unittest.TestCase):
    def test_consume_within_cap(self):
        ledger = Ledger(DailyCaps(llm=5), "2026-08-04")
        ledger.consume(Resource.LLM, 3, reason="精评")
        self.assertEqual(ledger.spent(Resource.LLM), 3)
        self.assertEqual(ledger.remaining(Resource.LLM), 2)

    def test_exceeding_cap_raises_not_degrades(self):
        ledger = Ledger(DailyCaps(llm=2), "2026-08-04")
        ledger.consume(Resource.LLM, 2, reason="精评")
        with self.assertRaises(BudgetExhausted):
            ledger.consume(Resource.LLM, 1, reason="再来一次")

    def test_failed_consume_does_not_partially_deduct(self):
        ledger = Ledger(DailyCaps(llm=5), "2026-08-04")
        with self.assertRaises(BudgetExhausted):
            ledger.consume(Resource.LLM, 99, reason="超额")
        self.assertEqual(ledger.spent(Resource.LLM), 0)

    def test_reason_is_mandatory(self):
        ledger = Ledger(DailyCaps(), "2026-08-04")
        with self.assertRaises(ValueError):
            ledger.consume(Resource.LLM, 1, reason="  ")

    def test_ledger_is_auditable(self):
        ledger = Ledger(DailyCaps(), "2026-08-04")
        ledger.consume(Resource.SEARCH, 1, reason="露营 供给侧")
        self.assertEqual(ledger.entries()[0].reason, "露营 供给侧")

    def test_error_message_tells_caller_to_report_honestly(self):
        ledger = Ledger(DailyCaps(llm=1), "2026-08-04")
        ledger.consume(Resource.LLM, 1, reason="x")
        with self.assertRaises(BudgetExhausted) as ctx:
            ledger.consume(Resource.LLM, 1, reason="y")
        self.assertIn("不要降级凑数", str(ctx.exception))


class TestUnlimitedByDefault(unittest.TestCase):
    def test_default_caps_are_unlimited(self):
        caps = DailyCaps()
        for r in (Resource.SEARCH, Resource.FETCH, Resource.LLM):
            self.assertTrue(caps.is_unlimited(r))

    def test_unlimited_never_exhausts(self):
        ledger = Ledger(DailyCaps(), "2026-08-04")
        ledger.consume(Resource.LLM, 1_000_000, reason="全量精评")
        self.assertEqual(ledger.spent(Resource.LLM), 1_000_000)

    def test_the_83x_funnel_passes_when_unlimited(self):
        """默认不限时，1000 次精评不再被拦。"""
        stages = [
            FunnelStage("规则打分", 10_000, 1_000, None),
            FunnelStage("LLM精评", 1_000, 1_000, Resource.LLM, 1),
        ]
        self.assertTrue(assert_funnel_feasible(stages, DailyCaps()).feasible)

    def test_conservative_preset_still_available(self):
        caps = DailyCaps.conservative()
        self.assertEqual((caps.search, caps.fetch, caps.llm), (10, 30, 12))


class TestFunnelFeasibility(unittest.TestCase):
    def test_feasible_funnel_passes(self):
        stages = [
            FunnelStage("原始采集", 100_000, 100_000, Resource.FETCH, 0),
            FunnelStage("程序硬过滤", 100_000, 10_000, None),
            FunnelStage("规则打分", 10_000, 1_000, None),
            FunnelStage("LLM 精评", 1_000, 10, Resource.LLM, 1),
        ]
        plan = assert_funnel_feasible(stages, DailyCaps(llm=12, fetch=30))
        self.assertTrue(plan.feasible)

    def test_catches_the_12_vs_1000_contradiction(self):
        """「LLM≤12次/天」与「精评每天约1000次」不可能同真，启动即炸。"""
        stages = [
            FunnelStage("规则打分", 10_000, 1_000, None),
            FunnelStage("LLM 精评", 1_000, 1_000, Resource.LLM, 1),
        ]
        with self.assertRaises(BudgetMisconfigured) as ctx:
            assert_funnel_feasible(stages, DailyCaps(llm=12))
        self.assertIn("83 倍", str(ctx.exception))

    def test_funnel_cannot_widen(self):
        stages = [FunnelStage("怪级", 100, 500, None)]
        with self.assertRaises(BudgetMisconfigured):
            assert_funnel_feasible(stages, DailyCaps())

    def test_stage_inputs_must_chain(self):
        stages = [
            FunnelStage("一级", 1000, 100, None),
            FunnelStage("二级", 999, 10, None),
        ]
        with self.assertRaises(BudgetMisconfigured):
            assert_funnel_feasible(stages, DailyCaps())

    def test_empty_funnel_rejected(self):
        with self.assertRaises(ValueError):
            assert_funnel_feasible([], DailyCaps())


class TestValueRouting(unittest.TestCase):
    def test_only_top_scored_get_expensive_treatment(self):
        ledger = Ledger(DailyCaps(llm=2), "2026-08-04")
        scored = [("a", 10.0), ("b", 90.0), ("c", 50.0), ("d", 70.0)]
        escalated, skipped = select_for_escalation(scored, ledger)
        self.assertEqual(escalated, ("b", "d"))
        self.assertEqual(set(skipped), {"a", "c"})

    def test_skipped_are_reported_not_hidden(self):
        ledger = Ledger(DailyCaps(llm=1), "2026-08-04")
        _, skipped = select_for_escalation([("a", 1.0), ("b", 2.0)], ledger)
        self.assertEqual(len(skipped), 1)

    def test_deterministic_on_ties(self):
        ledger = Ledger(DailyCaps(llm=1), "2026-08-04")
        a, _ = select_for_escalation([("z", 5.0), ("a", 5.0)], ledger)
        self.assertEqual(a, ("a",))

    def test_empty_input(self):
        ledger = Ledger(DailyCaps(), "2026-08-04")
        self.assertEqual(select_for_escalation([], ledger), ((), ()))


class TestHonestCount(unittest.TestCase):
    def test_shortfall_is_stated_not_padded(self):
        count = honest_count(available=44, processed=44, skipped=0, target=50)
        self.assertFalse(count.met_target)
        self.assertIn("不凑数", count.line())

    def test_budget_skip_is_surfaced(self):
        count = honest_count(available=100, processed=12, skipped=88, target=50)
        self.assertIn("配额不足未处理 88 条", count.line())

    def test_inconsistent_counts_rejected(self):
        with self.assertRaises(ValueError):
            honest_count(available=10, processed=8, skipped=5, target=10)


if __name__ == "__main__":
    unittest.main()
