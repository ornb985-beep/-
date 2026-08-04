"""证据层测试 —— span grounding、时效衰减、双源锚定、真值发现。"""

from __future__ import annotations

import unittest

from oic.evidence import decay, truth
from oic.evidence.grounding import (
    Claim,
    RejectReason,
    expand_numbers,
    verify_batch,
    verify_claim,
)

RAW = "据榜单显示，该单品近30天销量为 3万单，客单价 129 元，退货率 8.5%。"


def claim_at(value: float, needle: str, text: str = RAW) -> Claim:
    start = text.index(needle)
    return Claim("C1", "月销量", value, "单", start, start + len(needle),
                 "https://example.com", "hash-abc")


class TestGrounding(unittest.TestCase):
    def test_accepts_grounded_value(self):
        self.assertTrue(verify_claim(claim_at(30000, "3万"), RAW).accepted)

    def test_rejects_hallucinated_value(self):
        result = verify_claim(claim_at(50000, "3万"), RAW)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, RejectReason.VALUE_NOT_IN_SPAN)

    def test_rejects_rounded_value(self):
        """原文 2.8 万不能匹配声称的 3 万 —— 容差不覆盖四舍五入。"""
        text = "月销 2.8 万单"
        self.assertFalse(verify_claim(claim_at(30000, "2.8 万", text), text).accepted)

    def test_rejects_span_without_number(self):
        self.assertEqual(
            verify_claim(claim_at(30000, "据榜单显示"), RAW).reason,
            RejectReason.NO_NUMBER_IN_SPAN,
        )

    def test_rejects_stale_snapshot(self):
        stale = Claim("C2", "月销量", 30000, "单",
                      RAW.index("3万"), RAW.index("3万") + 2,
                      "https://example.com", "hash-OLD")
        self.assertEqual(
            verify_claim(stale, RAW, expected_snapshot_hash="hash-abc").reason,
            RejectReason.SNAPSHOT_MISMATCH,
        )

    def test_unit_expansion(self):
        self.assertIn(30000.0, expand_numbers("3万单"))
        self.assertIn(3.0, expand_numbers("3万单"))
        self.assertIn(1.5e8, expand_numbers("1.5亿元"))

    def test_fullwidth_digits(self):
        text = "客单价 １２９ 元"
        self.assertTrue(verify_claim(claim_at(129, "１２９", text), text).accepted)

    def test_batch_flags_high_rejection_rate(self):
        claims = [claim_at(30000, "3万")] + [claim_at(999999, "3万") for _ in range(3)]
        batch = verify_batch(claims, RAW)
        self.assertGreater(batch.rejection_rate, 0.3)
        self.assertTrue(any("提示词" in line for line in batch.summary()))


class TestDecay(unittest.TestCase):
    def test_fresh_evidence_full_weight(self):
        self.assertAlmostEqual(decay.decay_weight(0), 1.0)

    def test_older_evidence_lower_weight(self):
        self.assertLess(decay.decay_weight(180), decay.decay_weight(30))

    def test_half_life(self):
        lam = decay.DEFAULT_DECAY_LAMBDA
        self.assertAlmostEqual(decay.decay_weight(decay.half_life_days(lam), lam), 0.5,
                               places=6)

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            decay.decay_weight(-1)


class TestAnchoring(unittest.TestCase):
    def _datum(self, source_id, grade, value=100.0, age=10.0):
        return decay.Datum("露营灯", "月销量", value, source_id, grade, age)

    def test_reprints_do_not_create_fake_multisource(self):
        """同一来源的十篇转载仍只算一条。"""
        data = [self._datum("xinhua", "B") for _ in range(10)]
        result = decay.anchor(data)
        self.assertEqual(result.independent_sources, 1)
        self.assertFalse(result.anchored)

    def test_two_ab_sources_anchor(self):
        result = decay.anchor([self._datum("qcc", "A"), self._datum("caixin", "B")])
        self.assertTrue(result.anchored)

    def test_c_grade_never_anchors(self):
        """C 级只作线索不作证据 —— 十个自媒体也锚不住。"""
        data = [self._datum(f"blog{i}", "C") for i in range(10)]
        result = decay.anchor(data)
        self.assertEqual(result.independent_sources, 10)
        self.assertFalse(result.anchored)
        self.assertEqual(result.status, "待核实")

    def test_divergence_downweights(self):
        data = [
            self._datum("qcc", "A", value=100.0),
            self._datum("media", "B", value=200.0),
        ]
        result = decay.anchor(data)
        self.assertTrue(result.divergent)
        self.assertTrue(any("口径差异" in line for line in result.explanation))

    def test_mixed_entities_rejected(self):
        with self.assertRaises(ValueError):
            decay.anchor([
                decay.Datum("A", "m", 1, "s1", "A", 1),
                decay.Datum("B", "m", 1, "s2", "A", 1),
            ])

    def test_fingerprint_is_stable_and_case_insensitive(self):
        self.assertEqual(decay.fingerprint("露营灯", "月销量"),
                         decay.fingerprint(" 露营灯 ", "月销量"))


class TestTruthDiscovery(unittest.TestCase):
    def test_small_source_count_falls_back(self):
        estimate = truth.discover([
            truth.Observation("a", 100.0),
            truth.Observation("b", 110.0),
        ])
        self.assertEqual(estimate.method, "prior_weighted")

    def test_outlier_source_downweighted(self):
        estimate = truth.discover([
            truth.Observation("a", 100.0),
            truth.Observation("b", 102.0),
            truth.Observation("c", 98.0),
            truth.Observation("liar", 100000.0),
        ])
        weights = dict(estimate.source_weights)
        self.assertLess(weights["liar"], weights["a"])
        self.assertLess(estimate.value, 1000.0, "离群值不该把真值拖走")

    def test_deterministic(self):
        observations = [
            truth.Observation("a", 100.0),
            truth.Observation("b", 105.0),
            truth.Observation("c", 95.0),
            truth.Observation("d", 300.0),
        ]
        first = truth.discover(observations)
        second = truth.discover(observations)
        self.assertEqual(first.value, second.value)
        self.assertEqual(first.source_weights, second.source_weights)

    def test_source_cannot_inflate_by_posting_more(self):
        """同一来源多条只取中位数 —— 刷条数不能提高影响力。"""
        few = truth.discover([
            truth.Observation("a", 100.0),
            truth.Observation("b", 102.0),
            truth.Observation("spam", 500.0),
        ])
        many = truth.discover([
            truth.Observation("a", 100.0),
            truth.Observation("b", 102.0),
        ] + [truth.Observation("spam", 500.0) for _ in range(50)])
        self.assertEqual(few.value, many.value)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            truth.discover([])


if __name__ == "__main__":
    unittest.main()
