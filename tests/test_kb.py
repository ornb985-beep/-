"""知识库测试 —— 每一条都在证明「这道闸真的会拦」。

只测「合法输入能通过」是没有意义的：一个恒返回 True 的校验器也能过。
所以这里的主体是**反向测试** —— 构造违规输入，断言它必须被拒绝。
"""

from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from oic.kb import check as kbcheck
from oic.kb.check import Severity, check_all
from oic.kb.evolve import EvolveError, falsify, supersede
from oic.kb.index import render_index, render_manifest
from oic.kb.parse import EntryError, parse_entry, render_entry
from oic.kb.schema import (
    Band, Domain, Entry, Grade, Maturity, Status, Type,
    derive_band, next_id, relative_dir, validate_fields,
)
from oic.kb.store import Store, load, repo_root_from

ROOT = repo_root_from()

VALID = """---
id: K-ACQ-901
title: 测试条目
domain: acquisition
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 1
sources:
  - oic/kb/schema.py
iteration: 1
reviewed_on: 2026-08-05
---

## 断言
测试用。

## 依据
本文件。

## 边界：什么情况下它不成立
仅用于测试。
"""


def entry(**overrides) -> Entry:
    base = parse_entry(VALID, "kb/entries/verified/acquisition/K-ACQ-901.md")
    return replace(base, **overrides) if overrides else base


def store_of(*entries: Entry, known: tuple[str, ...] = ()) -> Store:
    return Store(root=ROOT, entries=tuple(entries), parse_errors=(), known_ids=known)


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------


class TestParse(unittest.TestCase):
    def test_parses_valid_entry(self):
        e = entry()
        self.assertEqual(e.id, "K-ACQ-901")
        self.assertEqual(e.domain, Domain.ACQUISITION)
        self.assertEqual(e.sources, ("oic/kb/schema.py",))

    def test_handwritten_confidence_rejected(self):
        """置信度必须是算出来的。**允许手填等于允许通胀。**"""
        for field in ("confidence", "certainty", "score", "reliability", "trust"):
            with self.assertRaises(EntryError) as ctx:
                parse_entry(VALID.replace("iteration: 1", f"{field}: 0.9\niteration: 1"))
            self.assertIn("禁止字段", str(ctx.exception))

    def test_missing_front_matter_rejected(self):
        with self.assertRaises(EntryError):
            parse_entry("## 断言\n没有 front-matter\n")

    def test_unclosed_front_matter_rejected(self):
        with self.assertRaises(EntryError):
            parse_entry("---\nid: K-ACQ-901\n\n## 断言\nx\n")

    def test_empty_body_rejected(self):
        """只有元数据的条目不承载知识。"""
        with self.assertRaises(EntryError):
            parse_entry("---\nid: K-ACQ-901\n---\n")

    def test_render_roundtrip_is_stable(self):
        """写回再解析必须得到同一条目 —— 否则演化操作会悄悄改内容。"""
        first = render_entry(entry())
        again = render_entry(parse_entry(first))
        self.assertEqual(first, again)

    def test_no_trailing_space_on_empty_fields(self):
        self.assertNotIn(": \n", render_entry(entry()))


# ---------------------------------------------------------------------------
# 字段校验
# ---------------------------------------------------------------------------


class TestFieldValidation(unittest.TestCase):
    def test_entry_without_source_rejected(self):
        """没有出处的条目不许存在。"""
        problems = validate_fields(entry(sources=(), n_independent_sources=0))
        self.assertTrue(any("没有出处" in p for p in problems))

    def test_independent_sources_cannot_exceed_listed(self):
        problems = validate_fields(entry(n_independent_sources=5))
        self.assertTrue(any("凭空多出来" in p for p in problems))

    def test_boundary_section_is_required(self):
        """没有边界的断言不是知识，是口号。"""
        problems = validate_fields(entry(body="## 断言\nx\n\n## 依据\ny\n"))
        self.assertTrue(any("边界" in p for p in problems))

    def test_falsified_requires_falsified_by(self):
        problems = validate_fields(entry(status=Status.FALSIFIED))
        self.assertTrue(any("falsified_by" in p for p in problems))

    def test_falsified_by_without_status_rejected(self):
        problems = validate_fields(entry(falsified_by="K-STA-016"))
        self.assertTrue(any("状态与证据不一致" in p for p in problems))

    def test_superseded_requires_superseded_by(self):
        problems = validate_fields(entry(status=Status.SUPERSEDED))
        self.assertTrue(any("superseded_by" in p for p in problems))

    def test_supersedes_requires_iteration_at_least_two(self):
        problems = validate_fields(entry(supersedes="K-ACQ-001", iteration=1))
        self.assertTrue(any("版次" in p for p in problems))

    def test_id_domain_code_must_match_domain(self):
        problems = validate_fields(entry(domain=Domain.STATISTICS))
        self.assertTrue(any("域码" in p for p in problems))

    def test_external_partition_must_be_external_maturity(self):
        """未经本项目验证的内容不得伪装成已验证。"""
        problems = validate_fields(entry(id="K-EXT-901", domain=Domain.EXTERNAL,
                                         maturity=Maturity.VERIFIED))
        self.assertTrue(any("maturity 必须是 external" in p for p in problems))

    def test_external_cannot_claim_grade_a(self):
        problems = validate_fields(entry(id="K-EXT-901", domain=Domain.EXTERNAL,
                                         maturity=Maturity.EXTERNAL,
                                         evidence_grade=Grade.A))
        self.assertTrue(any("不得标 A 级" in p for p in problems))

    def test_valid_entry_has_no_problems(self):
        self.assertEqual(validate_fields(entry()), [])


# ---------------------------------------------------------------------------
# 置信档位
# ---------------------------------------------------------------------------


class TestBand(unittest.TestCase):
    def test_falsified_overrides_everything(self):
        e = entry(status=Status.FALSIFIED, falsified_by="K-STA-016",
                  evidence_grade=Grade.A, sample_size=1000)
        self.assertEqual(derive_band(e), Band.FALSIFIED)

    def test_external_is_always_unverified(self):
        e = entry(id="K-EXT-901", domain=Domain.EXTERNAL,
                  maturity=Maturity.EXTERNAL, evidence_grade=Grade.B)
        self.assertEqual(derive_band(e), Band.UNVERIFIED)

    def test_prior_is_unverified(self):
        self.assertEqual(derive_band(entry(maturity=Maturity.PRIOR)), Band.UNVERIFIED)

    def test_fact_needs_sample_and_sources_for_confirmed(self):
        """关于世界的断言要样本量。"""
        weak = entry(type=Type.FACT, n_independent_sources=1, sample_size=100)
        self.assertEqual(derive_band(weak), Band.PROVISIONAL)
        mid = entry(type=Type.FACT, n_independent_sources=2, sample_size=11,
                    sources=("a", "b"))
        self.assertEqual(derive_band(mid), Band.SUPPORTED)
        strong = entry(type=Type.FACT, n_independent_sources=2, sample_size=30,
                       sources=("a", "b"))
        self.assertEqual(derive_band(strong), Band.CONFIRMED)

    def test_system_behaviour_claim_needs_no_sample(self):
        """关于本系统行为的断言要的是测试，不是 30 个样本。

        「kelly 在 n<30 时拒绝输出」这条不需要 30 个样本来证明。
        """
        e = entry(type=Type.CRITERION, maturity=Maturity.VERIFIED,
                  evidence_grade=Grade.A, sample_size=None)
        self.assertEqual(derive_band(e), Band.CONFIRMED)

    def test_implemented_but_unproven_is_at_most_supported(self):
        e = entry(type=Type.METHOD, maturity=Maturity.IMPLEMENTED,
                  evidence_grade=Grade.A)
        self.assertEqual(derive_band(e), Band.SUPPORTED)

    def test_band_is_not_a_number(self):
        """刻意不给 0.87 —— 那是这套系统在别处拒绝的伪精确。"""
        self.assertIsInstance(entry().band, str)
        self.assertFalse(hasattr(entry(), "confidence"))


# ---------------------------------------------------------------------------
# 跨条目校验
# ---------------------------------------------------------------------------


class TestCrossEntryChecks(unittest.TestCase):
    def test_source_pointing_to_missing_file_rejected(self):
        """「看起来有依据」比「没有依据」更危险。"""
        report = check_all(store_of(entry(sources=("oic/不存在的文件.py",))))
        self.assertTrue(any(f.check == "sources" and f.severity == Severity.ERROR
                            for f in report.findings))

    def test_external_source_prefix_skips_file_check(self):
        report = check_all(store_of(entry(sources=("EXT:某篇论文",))))
        self.assertFalse(any(f.check == "sources" for f in report.findings))

    def test_empty_external_source_rejected(self):
        report = check_all(store_of(entry(sources=("EXT:",))))
        self.assertTrue(any(f.check == "sources" for f in report.findings))

    def test_duplicate_ids_detected(self):
        a = entry(path="kb/a.md")
        b = entry(path="kb/b.md")
        report = check_all(store_of(a, b))
        self.assertTrue(any(f.check == "unique_id" for f in report.findings))

    def test_external_cannot_be_sole_basis_of_verified(self):
        """收录通用方法论之后最关键的一道闸。"""
        ext = entry(id="K-EXT-901", domain=Domain.EXTERNAL,
                    maturity=Maturity.EXTERNAL, evidence_grade=Grade.B,
                    path="kb/entries/external/K-EXT-901.md")
        derived = entry(sources=("kb/entries/external/K-EXT-901.md",))
        report = check_all(store_of(ext, derived))
        self.assertTrue(any(f.check == "external_isolation"
                            and f.severity == Severity.ERROR
                            for f in report.findings))

    def test_external_plus_own_evidence_is_allowed(self):
        ext = entry(id="K-EXT-901", domain=Domain.EXTERNAL,
                    maturity=Maturity.EXTERNAL, evidence_grade=Grade.B,
                    path="kb/entries/external/K-EXT-901.md")
        derived = entry(sources=("kb/entries/external/K-EXT-901.md",
                                 "oic/kb/schema.py"),
                        n_independent_sources=2)
        report = check_all(store_of(ext, derived))
        self.assertFalse(any(f.check == "external_isolation" for f in report.findings))

    def test_deleted_entry_id_detected(self):
        """号码本里有、库里没有 → 有人删了条目。"""
        report = check_all(store_of(entry(), known=("K-ACQ-901", "K-ACQ-902")))
        self.assertTrue(any(f.check == "no_deletion" and f.subject == "K-ACQ-902"
                            and f.severity == Severity.ERROR
                            for f in report.findings))

    def test_link_to_missing_entry_detected(self):
        report = check_all(store_of(entry(supersedes="K-ACQ-888", iteration=2)))
        self.assertTrue(any(f.check == "links" for f in report.findings))

    def test_one_way_supersede_link_detected(self):
        old = entry(id="K-ACQ-902", status=Status.SUPERSEDED, superseded_by="")
        new = entry(supersedes="K-ACQ-902", iteration=2)
        report = check_all(store_of(old, new))
        self.assertTrue(any("单向链" in f.message for f in report.findings))

    def test_superseded_target_must_not_stay_active(self):
        old = entry(id="K-ACQ-902", status=Status.ACTIVE, superseded_by="K-ACQ-901")
        new = entry(supersedes="K-ACQ-902", iteration=2)
        report = check_all(store_of(old, new))
        self.assertTrue(any("仍是 active" in f.message for f in report.findings))

    def test_supersede_chain_cycle_detected(self):
        a = entry(id="K-ACQ-901", supersedes="K-ACQ-902", iteration=2,
                  status=Status.SUPERSEDED, superseded_by="K-ACQ-902")
        b = entry(id="K-ACQ-902", supersedes="K-ACQ-901", iteration=2,
                  status=Status.SUPERSEDED, superseded_by="K-ACQ-901")
        report = check_all(store_of(a, b))
        self.assertTrue(any("成环" in f.message for f in report.findings))


# ---------------------------------------------------------------------------
# playbook 引用
# ---------------------------------------------------------------------------


class TestPlaybookReferences(unittest.TestCase):
    def _findings(self, text: str, entries):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kb" / "playbooks").mkdir(parents=True)
            (root / "kb" / "playbooks" / "P0-测试.md").write_text(text, encoding="utf-8")
            store = Store(root=root, entries=tuple(entries), parse_errors=(),
                          known_ids=())
            return kbcheck.check_playbooks(store)

    def test_broken_reference_detected(self):
        found = self._findings("引用 [K-ACQ-888] 不存在", [entry()])
        self.assertTrue(any(f.severity == Severity.ERROR for f in found))

    def test_reference_to_falsified_without_note_is_error(self):
        """读者是按行读的 —— 不标状态就会被当成现行结论。"""
        dead = entry(id="K-ACQ-902", status=Status.FALSIFIED,
                     falsified_by="K-ACQ-901", maturity=Maturity.FALSIFIED)
        found = self._findings("按 [K-ACQ-902] 执行即可", [dead])
        self.assertTrue(any(f.severity == Severity.ERROR for f in found))

    def test_reference_to_falsified_with_note_is_allowed(self):
        """讲教训时就该指向那条 —— 只要同一行写明它已被推翻。"""
        dead = entry(id="K-ACQ-902", status=Status.FALSIFIED,
                     falsified_by="K-ACQ-901", maturity=Maturity.FALSIFIED)
        found = self._findings("一条已被推翻的结论：[K-ACQ-902]", [dead])
        self.assertEqual([f for f in found if f.severity == Severity.ERROR], [])

    def test_playbook_without_any_reference_warns(self):
        found = self._findings("这是一份没有引用任何条目的文档", [entry()])
        self.assertTrue(any(f.severity == Severity.WARN for f in found))


# ---------------------------------------------------------------------------
# 演化
# ---------------------------------------------------------------------------


class TestEvolve(unittest.TestCase):
    def _sandbox(self):
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "kb" / relative_dir(Domain.ACQUISITION)).mkdir(parents=True)
        return tmp, root

    def test_supersede_requires_new_id(self):
        tmp, root = self._sandbox()
        with tmp:
            store = Store(root=root, entries=(entry(),), parse_errors=(), known_ids=())
            with self.assertRaises(EvolveError):
                supersede(store, "K-ACQ-901", entry(), "理由", "2026-08-05")

    def test_supersede_requires_reason(self):
        tmp, root = self._sandbox()
        with tmp:
            store = Store(root=root, entries=(entry(),), parse_errors=(), known_ids=())
            with self.assertRaises(EvolveError):
                supersede(store, "K-ACQ-901", entry(id="K-ACQ-902"), "  ", "2026-08-05")

    def test_supersede_marks_old_and_links_both_ways(self):
        tmp, root = self._sandbox()
        with tmp:
            store = Store(root=root, entries=(entry(),), parse_errors=(), known_ids=())
            supersede(store, "K-ACQ-901", entry(id="K-ACQ-902"),
                      "有了更好的说法", "2026-08-05")
            reloaded = load(root).by_id
            self.assertEqual(reloaded["K-ACQ-901"].status, Status.SUPERSEDED)
            self.assertEqual(reloaded["K-ACQ-901"].superseded_by, "K-ACQ-902")
            self.assertEqual(reloaded["K-ACQ-902"].supersedes, "K-ACQ-901")
            self.assertGreaterEqual(reloaded["K-ACQ-902"].iteration, 2)

    def test_falsify_keeps_original_body(self):
        """证伪不删除 —— 原文必须原样保留。"""
        tmp, root = self._sandbox()
        with tmp:
            victim = entry(id="K-ACQ-901")
            killer = entry(id="K-ACQ-902")
            store = Store(root=root, entries=(victim, killer), parse_errors=(),
                          known_ids=())
            falsify(store, "K-ACQ-901", "K-ACQ-902", "被新数据推翻", "2026-08-05")
            updated = load(root).by_id["K-ACQ-901"]
            self.assertEqual(updated.status, Status.FALSIFIED)
            self.assertEqual(updated.falsified_by, "K-ACQ-902")
            self.assertIn("测试用", updated.body)          # 原文还在
            self.assertIn("已证伪", updated.body)

    def test_falsify_requires_existing_evidence(self):
        tmp, root = self._sandbox()
        with tmp:
            store = Store(root=root, entries=(entry(),), parse_errors=(), known_ids=())
            with self.assertRaises(EvolveError):
                falsify(store, "K-ACQ-901", "K-ACQ-888", "理由", "2026-08-05")

    def test_entry_cannot_falsify_itself(self):
        tmp, root = self._sandbox()
        with tmp:
            store = Store(root=root, entries=(entry(),), parse_errors=(), known_ids=())
            with self.assertRaises(EvolveError):
                falsify(store, "K-ACQ-901", "K-ACQ-901", "理由", "2026-08-05")

    def test_no_delete_function_exists(self):
        """没有 delete 不是疏漏。"""
        import oic.kb.evolve as evolve

        for name in ("delete", "remove", "drop", "purge"):
            self.assertFalse(hasattr(evolve, name), f"evolve 不应有 {name}")


# ---------------------------------------------------------------------------
# 索引确定性
# ---------------------------------------------------------------------------


class TestIndexDeterminism(unittest.TestCase):
    def setUp(self):
        self.store = load(ROOT)

    def test_index_is_byte_identical_on_rerun(self):
        """索引重跑必须逐字节一致 —— 否则 git diff 里永远有噪声。"""
        self.assertEqual(render_index(self.store), render_index(self.store))

    def test_index_contains_no_timestamp(self):
        """不写生成时间：那会让每次重建都产生 diff，而 git 已经记录了时间。"""
        text = render_index(self.store)
        for marker in ("生成于", "2026-08-05T", "Generated at"):
            self.assertNotIn(marker, text)

    def test_manifest_only_grows(self):
        store = Store(root=ROOT, entries=(entry(),), parse_errors=(),
                      known_ids=("K-ACQ-800",))
        text = render_manifest(store)
        self.assertIn("K-ACQ-800", text)      # 历史 id 不会被新库覆盖掉
        self.assertIn("K-ACQ-901", text)

    def test_next_id_never_reuses(self):
        self.assertEqual(next_id(Domain.ACQUISITION, ("K-ACQ-001", "K-ACQ-003")),
                         "K-ACQ-004")


# ---------------------------------------------------------------------------
# 真实知识库
# ---------------------------------------------------------------------------


class TestRealKnowledgeBase(unittest.TestCase):
    def setUp(self):
        self.store = load(ROOT)

    def test_no_parse_errors(self):
        self.assertEqual(self.store.parse_errors, ())

    def test_all_six_checks_pass(self):
        report = check_all(self.store)
        self.assertTrue(report.clean, "\n".join(f.line() for f in report.errors))
        self.assertEqual(report.warnings, ())

    def test_has_substantial_content(self):
        self.assertGreaterEqual(len(self.store.entries), 200)

    def test_every_domain_populated(self):
        for domain in ("acquisition", "evidence", "metrics", "statistics",
                       "analysis", "compliance", "orchestration", "delivery",
                       "governance", "external"):
            self.assertTrue(self.store.domain(domain), f"{domain} 无条目")

    def test_falsified_entry_is_kept_as_acceptance_sample(self):
        """那次 ρ 翻转必须留在库里 —— 它是「证伪不删除」的验收样本。"""
        falsified = self.store.falsified
        self.assertTrue(falsified, "库里应当保留至少一条被推翻的结论")
        for e in falsified:
            self.assertTrue(e.falsified_by)
            self.assertIn(e.falsified_by, self.store.by_id)
            self.assertEqual(e.band, Band.FALSIFIED)

    def test_chain_traces_back_to_origin(self):
        for e in self.store.entries:
            chain = self.store.chain(e.id)
            self.assertEqual(chain[-1].id, e.id)

    def test_external_entries_are_physically_isolated(self):
        for e in self.store.external:
            self.assertIn("entries/external/", e.path)
            self.assertNotEqual(e.evidence_grade, Grade.A)

    def test_no_verified_entry_claims_external_maturity(self):
        for e in self.store.entries:
            if "entries/verified/" in e.path:
                self.assertNotEqual(e.maturity, Maturity.EXTERNAL, e.id)

    def test_every_entry_has_boundary_section(self):
        for e in self.store.entries:
            self.assertIn("## 边界", e.body, f"{e.id} 缺边界小节")

    def test_every_repo_source_path_exists(self):
        for e in self.store.entries:
            for source in e.sources:
                if source.startswith("EXT:"):
                    continue
                target = source.split("#", 1)[0].split("::", 1)[0]
                self.assertTrue((ROOT / target).exists(),
                                f"{e.id} 的出处不存在：{target}")

    def test_index_file_matches_current_entries(self):
        """INDEX.md 必须是最新的 —— 否则它会误导读者。"""
        on_disk = (ROOT / "kb" / "INDEX.md").read_text(encoding="utf-8")
        self.assertEqual(on_disk, render_index(self.store),
                         "INDEX.md 已过期，请运行 python -m oic.kb --index")

    def test_sdk_exposes_knowledge(self):
        from oic.sdk import OIC

        oic = OIC.for_app(app_name="KB-Test", contact="t@example.com")
        kb = oic.knowledge()
        self.assertGreaterEqual(len(kb.entries), 200)
        self.assertTrue(kb.select(domain="governance", type="criterion"))


if __name__ == "__main__":
    unittest.main()
