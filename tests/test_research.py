"""采集归一层测试 —— 重点是"拒绝"行为对不对。"""

from __future__ import annotations

import unittest

from oic.research import metrics as mx
from oic.research.asof import (
    LookaheadError,
    assert_no_lookahead,
    is_available_at,
    parse_iso_date,
)
from oic.research.backtest import auc, rank, spearman
from oic.research.dossier import Observation, build_dossier, resolve
from oic.research.units import Currency, UnitError, parse_percent, parse_quantity


def obs(cat, key, year, val, src, grade="B", pub="2022-06-01", currency="CNY"):
    return Observation(
        category_key=cat, metric_family=key.family, metric_scope=key.scope,
        metric_measure=key.measure, year=year, value=val, currency=currency,
        unit_note="", source_url=f"https://example.com/{src}", source_name=src,
        source_grade=grade, published_at=pub, retrieved_at="2026-08-04",
        snippet=f"{val}",
    )


class TestUnits(unittest.TestCase):
    def test_scale_words(self):
        self.assertAlmostEqual(parse_quantity("226.94 亿元", 2022).value, 2.2694e10, delta=1)
        self.assertAlmostEqual(parse_quantity("1 万亿元", 2026).value, 1e12, delta=1)
        self.assertAlmostEqual(parse_quantity("100 万家", 2022).value, 1e6, delta=1)

    def test_wan_yi_not_truncated_to_wan(self):
        """「万亿」不得被「万」截断 —— 会差 8 个数量级。"""
        self.assertAlmostEqual(parse_quantity("1 万亿元", 2026).value, 1e12, delta=1)

    def test_usd_not_misread_as_cny(self):
        """「亿美元」里含「元」字，必须先判美元。"""
        self.assertEqual(parse_quantity("28.4 亿美元", 2024).currency, Currency.USD)
        self.assertEqual(parse_quantity("226.94 亿元", 2022).currency, Currency.CNY)

    def test_count_has_no_currency(self):
        self.assertEqual(parse_quantity("6.4 万家", 2022).currency, Currency.NONE)

    def test_currency_conversion_is_flagged(self):
        converted = parse_quantity("28.4 亿美元", 2024).to_cny()
        self.assertTrue(converted.converted)
        self.assertEqual(converted.conversion_rate, 7.20)
        self.assertEqual(converted.original_currency, Currency.USD)

    def test_conversion_refuses_unknown_year(self):
        with self.assertRaises(UnitError):
            parse_quantity("10 亿美元", 1850).to_cny()

    def test_no_number_raises_not_zero(self):
        with self.assertRaises(UnitError):
            parse_quantity("市场规模持续增长", 2022)

    def test_percent_sign(self):
        self.assertAlmostEqual(parse_percent("同比增长 27.3%"), 27.3)
        self.assertAlmostEqual(parse_percent("同比下降 8.46%"), -8.46)
        self.assertAlmostEqual(parse_percent("增速回落 6.5%"), -6.5)


class TestMetricTaxonomy(unittest.TestCase):
    def test_same_key_merges(self):
        self.assertTrue(mx.MARKET_SIZE_CORE.mergeable_with(mx.MARKET_SIZE_CORE))

    def test_core_and_equipment_do_not_merge(self):
        """露营核心市场 1334亿 vs 装备市场 226.94亿 —— 不是偏差，是两个指标。"""
        self.assertFalse(mx.MARKET_SIZE_CORE.mergeable_with(mx.MARKET_SIZE_EQUIPMENT))
        with self.assertRaises(mx.MetricConflict):
            mx.assert_mergeable([mx.MARKET_SIZE_CORE, mx.MARKET_SIZE_EQUIPMENT])

    def test_stock_and_flow_do_not_merge(self):
        """存量/流量混淆会得出「新增330万家 > 存量100万家」的荒谬结论。"""
        with self.assertRaises(mx.MetricConflict):
            mx.assert_mergeable([mx.COMPANY_STOCK, mx.COMPANY_NEW])

    def test_conflict_message_names_the_difference(self):
        message = mx.explain_conflict(mx.COMPANY_STOCK, mx.COMPANY_NEW)
        self.assertIn("存量/流量", message)

    def test_classify_prefers_longer_phrase(self):
        self.assertEqual(mx.classify("核心市场规模"), mx.MARKET_SIZE_CORE)
        self.assertEqual(mx.classify("市场规模"), mx.MARKET_SIZE_ALL)

    def test_classify_returns_none_when_unknown(self):
        self.assertIsNone(mx.classify("某个没见过的指标"))


class TestAsOfGate(unittest.TestCase):
    def test_year_only_is_conservative(self):
        self.assertEqual(parse_iso_date("2022").isoformat(), "2022-12-31")

    def test_month_end_including_leap_year(self):
        self.assertEqual(parse_iso_date("2024-02").isoformat(), "2024-02-29")
        self.assertEqual(parse_iso_date("2022-02").isoformat(), "2022-02-28")
        self.assertEqual(parse_iso_date("2022-12").isoformat(), "2022-12-31")

    def test_availability(self):
        self.assertTrue(is_available_at("2022-01-13", "2022-12-31"))
        self.assertFalse(is_available_at("2025-04-14", "2022-12-31"))

    def test_as_of_gate_blocks_future_evidence(self):
        """把 2025 年的观测喂进 2022 as-of 评分，必须抛错。

        这是整个回测有效性的技术保障 —— 断言本身必须真的会失败。
        """
        with self.assertRaises(LookaheadError):
            assert_no_lookahead("2025-04-14", "2022-12-31", "预制菜规模")

    def test_dossier_enforces_gate(self):
        data = [
            obs("x", mx.MARKET_SIZE_ALL, 2022, 100.0, "a"),
            obs("x", mx.MARKET_SIZE_ALL, 2025, 300.0, "b", pub="2025-06-01"),
        ]
        with self.assertRaises(LookaheadError):
            build_dossier("x", "测试", data, "2022-12-31", enforce_gate=True)

    def test_dossier_allows_gate_off_for_outcomes(self):
        data = [obs("x", mx.MARKET_SIZE_ALL, 2025, 300.0, "b", pub="2025-06-01")]
        dossier = build_dossier("x", "测试", data, "2025-12-31", enforce_gate=False)
        self.assertEqual(dossier.n_observations_used, 1)


class TestDossier(unittest.TestCase):
    def test_conflicting_definitions_kept_separate(self):
        data = [
            obs("camping", mx.MARKET_SIZE_CORE, 2022, 1334e8, "bgao"),
            obs("camping", mx.MARKET_SIZE_EQUIPMENT, 2022, 226.94e8, "baogao"),
        ]
        dossier = build_dossier("camping", "露营", data, "2022-12-31")
        self.assertIsNotNone(dossier.value(mx.MARKET_SIZE_CORE, 2022))
        self.assertIsNotNone(dossier.value(mx.MARKET_SIZE_EQUIPMENT, 2022))
        # 两个值必须不同 —— 说明没有被平均掉
        self.assertNotAlmostEqual(
            dossier.value(mx.MARKET_SIZE_CORE, 2022),
            dossier.value(mx.MARKET_SIZE_EQUIPMENT, 2022),
        )

    def test_single_source_flagged_unanchored(self):
        data = [obs("x", mx.MARKET_SIZE_ALL, 2022, 100.0, "only")]
        dossier = build_dossier("x", "测试", data, "2022-12-31")
        self.assertFalse(dossier.get(mx.MARKET_SIZE_ALL, 2022).anchored)

    def test_two_ab_sources_anchor(self):
        data = [
            obs("x", mx.MARKET_SIZE_ALL, 2022, 100.0, "a", grade="A"),
            obs("x", mx.MARKET_SIZE_ALL, 2022, 110.0, "b", grade="B"),
        ]
        dossier = build_dossier("x", "测试", data, "2022-12-31")
        self.assertTrue(dossier.get(mx.MARKET_SIZE_ALL, 2022).anchored)

    def test_mixed_currency_refused(self):
        data = [
            obs("x", mx.MARKET_SIZE_ALL, 2021, 91e8, "a", currency="USD"),
            obs("x", mx.MARKET_SIZE_ALL, 2021, 600e8, "b", currency="CNY"),
        ]
        with self.assertRaises(ValueError):
            resolve(data, 2022)

    def test_growth_returns_none_when_year_missing(self):
        data = [obs("x", mx.MARKET_SIZE_ALL, 2022, 100.0, "a")]
        dossier = build_dossier("x", "测试", data, "2022-12-31")
        self.assertIsNone(dossier.growth_pct(mx.MARKET_SIZE_ALL, 2022, 2021))


class TestBacktestStatistics(unittest.TestCase):
    def test_rank_handles_ties(self):
        self.assertEqual(rank([10.0, 20.0, 20.0, 30.0]), [1.0, 2.5, 2.5, 4.0])

    def test_spearman_perfect(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)

    def test_spearman_refuses_tiny_sample(self):
        with self.assertRaises(ValueError):
            spearman([1, 2], [3, 4])

    def test_spearman_refuses_constant_series(self):
        with self.assertRaises(ValueError):
            spearman([1, 1, 1, 1], [1, 2, 3, 4])

    def test_auc_perfect_and_random(self):
        self.assertAlmostEqual(auc([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0]), 1.0)
        self.assertAlmostEqual(auc([0.5, 0.5, 0.5, 0.5], [1, 1, 0, 0]), 0.5)

    def test_auc_refuses_single_class(self):
        with self.assertRaises(ValueError):
            auc([0.5, 0.6], [1, 1])


class TestBacktestIntegration(unittest.TestCase):
    def test_real_backtest_has_no_lookahead(self):
        """跑真实数据，断言 as-of 闸没有被绕过。"""
        from pathlib import Path

        from oic.research.backtest import (
            DATA_DIR,
            extract_signals,
            load_categories,
        )
        from oic.research.dossier import load_observations

        categories = load_categories(DATA_DIR / "categories.jsonl")
        observations = load_observations(DATA_DIR / "observations.jsonl")
        self.assertGreater(len(categories), 0, "样本池不应为空")
        # 不抛 LookaheadError 即为通过
        signals = extract_signals(categories, observations)
        self.assertEqual(len(signals), len(categories))

    def test_insufficient_categories_are_kept_in_denominator(self):
        """规则 E2：数据缺失的品类必须保留，不得静默删除。"""
        from oic.research.backtest import (
            DATA_DIR,
            extract_signals,
            load_categories,
        )
        from oic.research.dossier import load_observations

        categories = load_categories(DATA_DIR / "categories.jsonl")
        signals = extract_signals(
            categories, load_observations(DATA_DIR / "observations.jsonl")
        )
        self.assertEqual(len(signals), len(categories))
        self.assertTrue(any(s.insufficient for s in signals),
                        "应当有品类被标记为数据不足")


if __name__ == "__main__":
    unittest.main()
