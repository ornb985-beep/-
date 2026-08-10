"""合规内核测试 —— 证券边界、AI 双标识、数据源白名单。"""

from __future__ import annotations

import unittest

from oic.compliance import ai_labeling as lbl
from oic.compliance import provenance as prov
from oic.compliance import securities_guard as guard


class TestSecuritiesGuard(unittest.TestCase):
    def test_blocks_all_must_block_samples(self):
        for sample in guard._MUST_BLOCK:
            with self.subTest(sample=sample):
                self.assertTrue(guard.guard(sample).blocked)

    def test_zero_false_positives_on_business_analysis(self):
        """纯商业机会分析必须 0 误杀 —— 误杀会逼团队关掉这道闸。"""
        for sample in guard._MUST_PASS:
            with self.subTest(sample=sample):
                result = guard.guard(sample)
                self.assertFalse(
                    result.blocked,
                    f"误杀：{sample}\n{result.report()}",
                )

    def test_investment_word_alone_does_not_trigger(self):
        """「投资」二字本身不触发，证券关联才触发。"""
        self.assertFalse(guard.guard("这个项目值得投资 50 万元做验证").blocked)

    def test_risky_phrasing_rewritten_not_blocked(self):
        result = guard.guard("本报告提供投资级决策建议")
        self.assertFalse(result.blocked)
        self.assertIn("商业/市场机会分析", result.text)

    def test_assert_safe_raises_on_hard_violation(self):
        with self.assertRaises(PermissionError):
            guard.assert_safe("建议买入 sh600519，目标价 2000 元")

    def test_violations_sorted_deterministically(self):
        text = "建议买入 sh600519，现在是买入时机，目标价 2000 元"
        first = guard.scan(text)
        second = guard.scan(text)
        self.assertEqual(first, second)


class TestAiLabeling(unittest.TestCase):
    def setUp(self):
        self.provider = lbl.ProviderIdentity(name="OIC", code="ALG-BEIAN-0001")

    def test_dual_label_applied(self):
        content = lbl.label("剪刀差 33%，窗口开着。", self.provider, "2026-08-04T00:00:00Z")
        self.assertIn(lbl.EXPLICIT_NOTICE, content.body)
        self.assertEqual(content.metadata["AIGC-Provider-Code"], "ALG-BEIAN-0001")
        self.assertTrue(content.metadata["AIGC-Content-ID"].startswith("OIC-"))

    def test_explicit_label_at_both_ends(self):
        body = lbl.add_explicit_label("正文")
        self.assertTrue(body.startswith(f"【{lbl.EXPLICIT_NOTICE}】"))
        self.assertTrue(body.endswith(f"【{lbl.EXPLICIT_NOTICE}】"))

    def test_label_is_idempotent(self):
        once = lbl.add_explicit_label("正文")
        twice = lbl.add_explicit_label(once)
        self.assertEqual(once, twice)

    def test_content_id_deterministic(self):
        a = lbl.content_id("同一份报告", self.provider)
        b = lbl.content_id("同一份报告", self.provider)
        self.assertEqual(a, b, "同一报告重新导出必须得到同一编号，否则无法审计对账")

    def test_content_id_changes_with_body(self):
        self.assertNotEqual(
            lbl.content_id("报告 A", self.provider),
            lbl.content_id("报告 B", self.provider),
        )

    def test_export_gate_rejects_missing_explicit_label(self):
        naked = lbl.LabeledContent("没有标识的正文", {"AIGC-Attribute": "x"})
        with self.assertRaises(lbl.LabelingError):
            lbl.assert_labeled(naked)

    def test_export_gate_rejects_missing_metadata(self):
        partial = lbl.LabeledContent(lbl.add_explicit_label("正文"), {})
        with self.assertRaises(lbl.LabelingError):
            lbl.assert_labeled(partial)

    def test_provider_identity_requires_code(self):
        with self.assertRaises(ValueError):
            lbl.ProviderIdentity(name="OIC", code="  ")


class TestProvenance(unittest.TestCase):
    def setUp(self):
        self.registry = prov.default_registry()

    def test_unregistered_source_blocked(self):
        with self.assertRaises(prov.SourceNotRegistered):
            self.registry.assert_source_allowed("taobao_scrape")

    def test_no_source_cleared_at_start(self):
        """起点上没有任何源被放行 —— 法务过完之前采集层不该能跑。"""
        self.assertEqual(self.registry.allowed_keys(), ())

    def test_scraping_never_allowed_even_if_cleared(self):
        self.registry.register(prov.SourceRecord(
            key="scrape_anything", name="某爬取源",
            access_method=prov.AccessMethod.SCRAPING,
            tos_url="https://example.com/tos",
            legal_status=prov.LegalStatus.CLEARED,
            legal_note="法务说没问题", reviewed_on="2026-08-04",
        ))
        with self.assertRaises(prov.SourceNotAllowed) as ctx:
            self.registry.assert_source_allowed("scrape_anything")
        self.assertIn("爬取", str(ctx.exception))

    def test_cleared_official_api_allowed(self):
        self.registry.register(prov.SourceRecord(
            key="qcc_open", name="企查查开放平台",
            access_method=prov.AccessMethod.OFFICIAL_API,
            tos_url="https://example.com/tos",
            legal_status=prov.LegalStatus.CLEARED,
            legal_note="已购企业版", reviewed_on="2026-08-04",
        ))
        record = self.registry.assert_source_allowed("qcc_open")
        self.assertTrue(record.allowed)

    def test_sensitive_pi_requires_pipia(self):
        self.registry.register(prov.SourceRecord(
            key="resume", name="简历",
            access_method=prov.AccessMethod.USER_PROVIDED,
            tos_url="https://example.com/tos",
            legal_status=prov.LegalStatus.CLEARED,
            legal_note="用户授权", reviewed_on="2026-08-04",
            handles_personal_info=True, handles_sensitive_pi=True,
            pipia_completed=False,
        ))
        with self.assertRaises(prov.SourceNotAllowed) as ctx:
            self.registry.assert_source_allowed("resume")
        self.assertIn("PIPIA", str(ctx.exception))

    def test_missing_tos_blocks(self):
        self.registry.register(prov.SourceRecord(
            key="mystery", name="来路不明",
            access_method=prov.AccessMethod.OFFICIAL_API,
            tos_url="", legal_status=prov.LegalStatus.CLEARED,
            legal_note="", reviewed_on="2026-08-04",
        ))
        with self.assertRaises(prov.SourceNotAllowed):
            self.registry.assert_source_allowed("mystery")

    def test_resale_source_is_flagged_as_blocker(self):
        """后悔信号当前设想为爬取 —— 必须显式挡住，而不是悄悄放行。"""
        record = self.registry.get("secondhand_resale")
        self.assertFalse(record.allowed)
        self.assertTrue(any("爬取" in reason for reason in record.blockers()))


if __name__ == "__main__":
    unittest.main()
