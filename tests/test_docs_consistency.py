"""文档一致性 —— 让「文档撒谎」从静默变成红色。

## 为什么需要这个

盘点时发现：`docs/v4/05` 与 `07` 写着「154 项测试」，`11` 写着「360 项」，
而实际是 423。三个数字，三个都错，**没有任何机制会告诉任何人**。

问题不是「数字错了」，是**同一个数字散在四处，改一处忘三处**。

解法不是更勤快地维护，是把数字**收敛到一处并由测试守着**：

    README.md 保留精确数字，且必须与实际一致
    其余文档不得再出现「N 项测试」

代价是每次加测试要改一处 README。这点摩擦是刻意的 ——
它保证那个数字永远是真的。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: 匹配「423 项测试」「154 项，全绿」这类断言
TEST_COUNT = re.compile(r"(\d{2,5})\s*项")

#: 一行里出现数字 + 这些词之一，才算「声称了测试数量」。
#: 初版只认「项测试」四个字，漏掉了 05 号的 `# 154 项，全绿` —— 检测器自己也会有缺口。
TEST_CONTEXT = ("测试", "unittest", "全绿")

#: 文档里出现测试数字的合法位置。**只有这一处。**
CANONICAL = REPO / "README.md"


def collect_test_count() -> int:
    """实际收集到的测试数。用 unittest 自己的发现机制，不猜。"""
    loader = unittest.TestLoader()
    suite = loader.discover(str(REPO / "tests"), top_level_dir=str(REPO))

    def count(item) -> int:
        if isinstance(item, unittest.TestSuite):
            return sum(count(child) for child in item)
        return 1

    return count(suite)


def docs_other_than_readme() -> list[Path]:
    out = sorted((REPO / "docs").rglob("*.md"))
    out.extend(sorted((REPO / "kb").glob("*.md")))
    out.extend(sorted((REPO / "kb" / "playbooks").glob("*.md")))
    return out


class TestDocumentedTestCount(unittest.TestCase):
    def test_readme_test_count_matches_reality(self):
        """README 里声称的测试数必须等于实际。

        这条会在每次加测试时变红。**那正是它存在的意义** ——
        改一个数字的成本，远低于一份持续撒谎的文档。
        """
        actual = collect_test_count()
        text = CANONICAL.read_text(encoding="utf-8")
        claimed = [int(m.group(1)) for m in TEST_COUNT.finditer(text)]

        self.assertTrue(claimed,
                        "README 里找不到测试数量声明 —— "
                        "这个数字应当集中在这一处")
        for number in claimed:
            self.assertEqual(
                number, actual,
                f"README 声称 {number} 项测试，实际 {actual} 项。"
                f"请把 README 里的数字改成 {actual}。")

    def test_no_other_doc_claims_a_test_count(self):
        """数字不得重新扩散到其他文档。

        允许在别处出现，就等于允许它们各自过期 ——
        而那正是这次盘点发现的状况（154 / 154 / 360，全错）。
        """
        offenders: list[str] = []
        for path in docs_other_than_readme():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not any(word in line for word in TEST_CONTEXT):
                    continue
                if TEST_COUNT.search(line):
                    rel = path.relative_to(REPO)
                    offenders.append(f"{rel}: {line.strip()}")
        self.assertEqual(
            offenders, [],
            "以下文档出现了具体测试数量，请改成不带数字的表述"
            "（数字只在 README 里维护）：\n  " + "\n  ".join(offenders))


class TestKnowledgeBaseIsLinked(unittest.TestCase):
    """知识库必须能从文档体系走到，否则没人会用。"""

    def test_readme_links_to_knowledge_base(self):
        text = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("kb/README.md", text)

    def test_docs_index_links_to_knowledge_base(self):
        """docs/v4 里至少有一处指向知识库。"""
        hits = [p for p in (REPO / "docs").rglob("*.md")
                if "kb/" in p.read_text(encoding="utf-8")]
        self.assertTrue(hits, "docs/ 里没有任何一处指向 kb/ —— "
                              "知识库会变成没人知道的孤岛")


class TestCiCoversTheGates(unittest.TestCase):
    """CI 必须真的跑那些闸门 —— 否则它们只在有人记得时才生效。"""

    def setUp(self):
        path = REPO / ".github" / "workflows" / "ci.yml"
        self.assertTrue(path.is_file(), "缺少 CI workflow")
        self.text = path.read_text(encoding="utf-8")

    def test_ci_runs_full_test_suite(self):
        self.assertIn("unittest discover -s tests", self.text)

    def test_ci_runs_knowledge_base_check(self):
        self.assertIn("oic.kb --check", self.text)

    def test_ci_verifies_index_is_current(self):
        """索引过期必须让 CI 红，否则读者会看到与实际不符的内容。"""
        self.assertIn("oic.kb --index", self.text)
        self.assertIn("git diff --exit-code", self.text)

    def test_ci_runs_every_selftest_module(self):
        """每个自检都在断言「这道闸真的会拦」，一个都不能漏。"""
        expected = (
            "oic.calibration.report",
            "oic.compliance.securities_guard",
            "oic.evidence.grounding",
            "oic.research.audit",
            "oic.research.units",
            "oic.scoring.kelly",
            "oic.sources.filing_parse",
            "oic.stats.overfit",
            "oic.kb",
        )
        missing = [m for m in expected if f"{m} --selftest" not in self.text]
        self.assertEqual(missing, [], f"CI 漏了这些自检：{missing}")

    def test_ci_has_no_third_party_install(self):
        """零第三方依赖是这个仓库的硬约束，CI 里出现 pip install 即是破坏。

        只看非注释行。初版直接扫全文，结果被 workflow 里那句
        「没有 pip install 这一步 —— 这是刻意的设计」判成违规 ——
        **解释某物不存在的注释，被当成了它存在的证据。**
        误报会把人逼着关掉闸门（K-GOV-013），所以修检测器，不是改注释。
        """
        code = [line for line in self.text.splitlines()
                if not line.lstrip().startswith("#")]
        offenders = [line.strip() for line in code if "pip install" in line]
        self.assertEqual(offenders, [],
                         f"CI 里出现了第三方依赖安装：{offenders}")


if __name__ == "__main__":
    unittest.main()
