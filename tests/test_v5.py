"""v5 测试：纠错内核、量化统计、招股书解析、交付层。"""

from __future__ import annotations

import re
import unittest

from oic.compliance import provenance as prov
from oic.config import CONSUMER_GOODS
from oic.deliver.plan_90day import Assumption, build_plan
from oic.deliver.resourcing import build_resource_plan
from oic.research import metrics as mx
from oic.research.audit import Severity, audit
from oic.research.dossier import Observation
from oic.sources.fetchers import (
    FetchError,
    FilingRef,
    edgar_submissions_url,
    fetch_filing,
    parse_edgar_submissions,
)
from oic.sources.filing_parse import FIXTURE_CN, extract_facts, split_sections
from oic.stats.overfit import (
    benjamini_hochberg,
    expected_max_correlation,
    probability_of_overfit,
)
from oic.stats.resample import bootstrap_ci, permutation_test_binary


def obs(category, key, year, value, source, snippet, currency="NONE"):
    return Observation(
        category_key=category, metric_family=key.family, metric_scope=key.scope,
        metric_measure=key.measure, year=year, value=value, currency=currency,
        unit_note="", source_url="https://example.com", source_name=source,
        source_grade="B", published_at="2022-06-01", retrieved_at="2026-08-04",
        snippet=snippet,
    )


class TestAuditCatchesMyOwnError(unittest.TestCase):
    """纠错内核必须能抓住我实际犯过的那个 100× 错误。"""

    def test_audit_catches_unit_error(self):
        bad = obs("camping", mx.COMPANY_NEW, 2022, 3_810_000.0, "cnfin",
                  "2022年露营相关企业注册同比增50.02%，达3.81万家")
        report = audit([bad])
        self.assertTrue(
            any(f.check == "grounding" and f.severity == Severity.ERROR
                for f in report.findings),
            "把「3.81万」记成 3,810,000 必须被字符级回验抓住",
        )

    def test_audit_passes_corrected_value(self):
        good = obs("camping", mx.COMPANY_NEW, 2022, 38_100.0, "cnfin",
                   "2022年露营相关企业注册同比增50.02%，达3.81万家")
        self.assertTrue(audit([good]).clean)

    def test_audit_catches_stock_flow_violation(self):
        data = [
            obs("camping", mx.COMPANY_NEW, 2022, 3_300_000.0, "a", "330万家"),
            obs("camping", mx.COMPANY_STOCK, 2022, 1_000_000.0, "b", "100万家"),
        ]
        self.assertTrue(any(f.check == "stock_flow" for f in audit(data).findings))

    def test_audit_catches_magnitude_gap(self):
        data = [
            obs("x", mx.MARKET_SIZE_ALL, 2022, 100.0, "a", "100"),
            obs("x", mx.MARKET_SIZE_ALL, 2022, 10_000.0, "b", "10000"),
        ]
        self.assertTrue(any(f.check == "magnitude" for f in audit(data).findings))

    def test_growth_rate_sign_is_not_a_false_positive(self):
        """「下滑70%」编码为 -70，符号来自文字不是数字，不该报错。"""
        data = [obs("nft", mx.DEMAND_GROWTH, 2022, -70.0, "a",
                    "销售额同比下滑70%左右")]
        self.assertTrue(audit(data).clean)

    def test_real_dataset_is_clean(self):
        """仓库里的真实观测必须无错误 —— 否则不能用于评分。"""
        from pathlib import Path

        from oic.research.backtest import DATA_DIR
        from oic.research.dossier import load_observations

        report = audit(load_observations(DATA_DIR / "observations.jsonl"))
        self.assertTrue(report.clean,
                        f"真实数据存在错误：{[f.line() for f in report.errors]}")


class TestResample(unittest.TestCase):
    def test_permutation_is_exact_for_small_n(self):
        import math
        result = permutation_test_binary([5, 4, 3, 2, 1, 0], [1, 1, 1, 0, 0, 0])
        self.assertTrue(result.exact)
        self.assertEqual(result.n_permutations, math.comb(6, 3))

    def test_perfect_separation_gives_smallest_possible_p(self):
        result = permutation_test_binary([5, 4, 3, 2, 1, 0], [1, 1, 1, 0, 0, 0])
        # 20 种排列里，只有 2 种（正负各一）达到 |ρ|=1
        self.assertAlmostEqual(result.p_value, 2 / 20)

    def test_real_backtest_result_is_not_significant(self):
        """实测 ρ=-0.293 必须判为不显著 —— 这是本项目最重要的一条断言。"""
        x = [52.0, 45.0, 28.67, 2.8, 0.3, -70.0]
        y = [0, 0, 1, 1, 1, 0]
        result = permutation_test_binary(x, y)
        self.assertAlmostEqual(result.statistic, -0.2928, places=3)
        self.assertGreater(result.p_value, 0.05)
        self.assertFalse(result.significant())

    def test_bootstrap_ci_spans_zero_on_noise(self):
        x = [52.0, 45.0, 28.67, 2.8, 0.3, -70.0]
        y = [0, 0, 1, 1, 1, 0]
        self.assertTrue(bootstrap_ci(x, y, n_resamples=2000).spans_zero)

    def test_constant_labels_rejected(self):
        with self.assertRaises(ValueError):
            permutation_test_binary([1, 2, 3, 4], [1, 1, 1, 1])

    def test_deterministic(self):
        x = [52.0, 45.0, 28.67, 2.8, 0.3, -70.0]
        y = [0, 0, 1, 1, 1, 0]
        a = bootstrap_ci(x, y, n_resamples=1000)
        b = bootstrap_ci(x, y, n_resamples=1000)
        self.assertEqual((a.lower, a.upper), (b.lower, b.upper))


class TestOverfit(unittest.TestCase):
    def test_more_features_raises_luck_baseline(self):
        one = expected_max_correlation(8, 1, n_simulations=400)
        many = expected_max_correlation(8, 20, n_simulations=400)
        self.assertGreater(many.p95_max_abs_rho, one.p95_max_abs_rho)

    def test_observed_rho_does_not_beat_luck(self):
        luck = expected_max_correlation(6, 1, n_simulations=1000)
        self.assertFalse(luck.beats_luck(0.293),
                         "n=6 时 |ρ|=0.293 不该被判为超过运气基线")

    def test_pbo_high_when_many_features_few_samples(self):
        import random
        rng = random.Random(7)
        noise = [[rng.gauss(0, 1) for _ in range(32)] for _ in range(20)]
        self.assertGreaterEqual(probability_of_overfit(noise, n_splits=8).pbo, 0.3)

    def test_pbo_low_when_one_strategy_truly_dominates(self):
        import random
        rng = random.Random(7)
        rows = [[rng.gauss(0, 1) for _ in range(32)] for _ in range(19)]
        rows.append([3.0 + rng.gauss(0, 0.05) for _ in range(32)])
        self.assertLess(probability_of_overfit(rows, n_splits=8).pbo, 0.2)

    def test_bh_is_monotone_and_conservative(self):
        corrected = benjamini_hochberg([("a", 0.01), ("b", 0.04), ("c", 0.5)])
        self.assertTrue(all(c.adjusted_p >= c.p_value - 1e-12 for c in corrected))

    def test_single_strategy_rejected(self):
        with self.assertRaises(ValueError):
            probability_of_overfit([[1.0, 2.0, 3.0, 4.0]])


class TestFilingParse(unittest.TestCase):
    def test_headings_must_be_short_lines(self):
        """正文里出现「市场规模」不得被当成章节标题。"""
        sections = split_sections(FIXTURE_CN, "zh")
        names = [s.name for s in sections]
        self.assertEqual(names.count("industry"), 1)
        self.assertEqual(names.count("competition"), 1)

    def test_no_headings_returns_empty(self):
        self.assertEqual(split_sections("一段没有标题的普通文字。", "zh"), ())

    def test_extracts_supply_side_fields(self):
        facts, _ = extract_facts(FIXTURE_CN, "zh")
        families = {f.metric_family for f in facts}
        self.assertIn(mx.Family.COMPANY_COUNT, families)
        self.assertIn(mx.Family.MARKET_SHARE, families)

    def test_cr5_and_own_share_kept_separate(self):
        facts, _ = extract_facts(FIXTURE_CN, "zh")
        cr5 = [f for f in facts if f.metric_key == mx.MARKET_SHARE_CR5]
        own = [f for f in facts if f.metric_key == mx.MARKET_SHARE_SELF]
        self.assertTrue(cr5 and abs(cr5[0].value - 18.5) < 1e-9)
        self.assertTrue(own and abs(own[0].value - 3.2) < 1e-9)

    def test_share_is_not_labelled_market_size(self):
        facts, _ = extract_facts(FIXTURE_CN, "zh")
        self.assertFalse(any(f.metric_family == mx.Family.MARKET_SIZE
                             and f.value in (3.2, 18.5) for f in facts))

    def test_soft_line_wrap_does_not_truncate(self):
        """「市场规模为\\n226.94亿元」是折行，不是句末。"""
        facts, _ = extract_facts(FIXTURE_CN, "zh")
        sizes = [f for f in facts if f.metric_family == mx.Family.MARKET_SIZE]
        self.assertTrue(sizes and abs(sizes[0].value - 2.2694e10) < 1)

    def test_span_never_crosses_sentence(self):
        facts, _ = extract_facts(FIXTURE_CN, "zh")
        for fact in facts:
            self.assertIsNone(re.search(r"[。；]", fact.quoted[:-1]),
                              f"span 跨句: {fact.quoted}")

    def test_filing_number_must_be_grounded(self):
        from oic.evidence.grounding import Claim, verify_claim
        fake = Claim("x", "market_size", 99999.0, "", 0, 60, "", "")
        self.assertFalse(verify_claim(fake, FIXTURE_CN).accepted)


class TestFetchers(unittest.TestCase):
    def test_edgar_url(self):
        self.assertEqual(edgar_submissions_url(320193),
                         "https://data.sec.gov/submissions/CIK0000320193.json")

    def test_edgar_rejects_bad_cik(self):
        with self.assertRaises(ValueError):
            edgar_submissions_url(0)

    def test_parse_submissions_selects_forms(self):
        payload = {
            "name": "ACME", "cik": 123,
            "filings": {"recent": {
                "form": ["S-1", "8-K", "10-K"],
                "filingDate": ["2021-03-01", "2021-04-01", "2022-02-01"],
                "accessionNumber": ["0001-21-000001", "0001-21-000002",
                                    "0001-22-000003"],
                "primaryDocument": ["s1.htm", "8k.htm", "10k.htm"],
            }},
        }
        refs = parse_edgar_submissions(payload)
        self.assertEqual({r.form_type for r in refs}, {"S-1", "10-K"})
        self.assertTrue(all(r.market == "US" for r in refs))

    def test_parse_submissions_detects_schema_drift(self):
        payload = {"name": "X", "cik": 1, "filings": {"recent": {
            "form": ["S-1", "10-K"], "filingDate": ["2021-01-01"],
            "accessionNumber": ["a"], "primaryDocument": ["b"],
        }}}
        with self.assertRaises(ValueError):
            parse_edgar_submissions(payload)

    def test_fetch_blocked_until_source_cleared(self):
        registry = prov.default_registry()
        ref = FilingRef("US", "ACME", "S-1", "2021-03-01",
                        "https://example.com/s1.htm", "sec_edgar")
        with self.assertRaises(prov.SourceNotAllowed):
            fetch_filing(ref, lambda url: "text", registry)

    def test_empty_response_is_an_error_not_a_conclusion(self):
        registry = prov.default_registry()
        registry.register(prov.SourceRecord(
            key="sec_edgar", name="SEC",
            access_method=prov.AccessMethod.PUBLIC_DOWNLOAD,
            tos_url="https://sec.gov/tos",
            legal_status=prov.LegalStatus.CLEARED,
            legal_note="", reviewed_on="2026-08-04",
        ))
        ref = FilingRef("US", "ACME", "S-1", "2021-03-01",
                        "https://example.com/s1.htm", "sec_edgar")
        with self.assertRaises(FetchError):
            fetch_filing(ref, lambda url: "   ", registry)

    def test_prospectus_sources_are_public_download_not_scraping(self):
        registry = prov.default_registry()
        for key in ("sec_edgar", "cninfo"):
            record = registry.get(key)
            self.assertEqual(record.access_method, prov.AccessMethod.PUBLIC_DOWNLOAD)


class TestDeliverables(unittest.TestCase):
    def _plan(self):
        return build_plan(
            "测试商机", CONSUMER_GOODS, 200_000.0,
            (Assumption("A", "留资率≥15%", "第7天留资<50 即证伪", 7),),
            "条件区间说明", "校准未建立",
        )

    def test_every_stage_has_a_stop_loss(self):
        for stage in self._plan().stages:
            self.assertTrue(stage.stop_loss.strip(),
                            "没有止损线的阶段不是计划，是许愿")

    def test_stage_budgets_sum_to_total(self):
        plan = self._plan()
        self.assertAlmostEqual(
            sum(s.budget_cap_rmb for s in plan.stages), plan.total_budget_rmb)

    def test_budgets_escalate_with_validation(self):
        """先小注试探，验证通过才加仓。"""
        caps = [s.budget_cap_rmb for s in self._plan().stages]
        self.assertEqual(caps, sorted(caps))

    def test_every_assumption_is_falsifiable(self):
        for assumption in self._plan().assumptions:
            self.assertTrue(assumption.falsified_when.strip())

    def test_resource_plan_flags_missing_priority_skill(self):
        plan = build_resource_plan(
            500_000.0, ("全栈开发",), "consumer_goods",
            (("阶段1", 20_000.0),),
        )
        # 爆品赛道第一优先是销售，团队只有工程 → 必须报警
        self.assertTrue(any("销售" in w for w in plan.warnings))

    def test_resource_plan_flags_overcommitment(self):
        plan = build_resource_plan(
            100_000.0, ("产品", "开发", "销售"), "consumer_goods",
            (("阶段1", 90_000.0),),
        )
        self.assertTrue(plan.warnings)

    def test_business_plans_pass_compliance_gates(self):
        from oic.compliance import ai_labeling as lbl
        from oic.compliance import securities_guard as sg
        from oic.deliver.business_plan import build_business_plans

        for plan in build_business_plans(top=3):
            body = plan.render()
            self.assertFalse(sg.guard(body).blocked, "BP 触发证券边界闸")
            content = lbl.label(body, lbl.ProviderIdentity("OIC", "X"), "2026-08-04")
            lbl.assert_labeled(content)

    def test_business_plan_refuses_point_predictions(self):
        """BP 里不得出现伪精确的收入点值。"""
        from oic.deliver.business_plan import build_business_plans

        for plan in build_business_plans(top=3):
            body = plan.render()
            self.assertIn("条件区间", body)
            self.assertIn("拒绝提供", body)

    def test_business_plan_cites_sources(self):
        from oic.deliver.business_plan import build_business_plans

        plans = build_business_plans(top=3)
        self.assertTrue(any(p.evidence for p in plans),
                        "至少应有商机带可追溯证据")
        for plan in plans:
            for ref in plan.evidence:
                self.assertTrue(ref.source_url.startswith("http"))


if __name__ == "__main__":
    unittest.main()
