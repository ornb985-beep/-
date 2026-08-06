"""知识库 CLI。

    python -m oic.kb --check      六条校验，有 ERROR 即退出码 1
    python -m oic.kb --index      重建 INDEX.md 与 IDS.txt
    python -m oic.kb --stats      各域条目数 / 类型 / 成熟度 / 档位分布
    python -m oic.kb --find 关键词  按标题与正文搜索
    python -m oic.kb --show ID    看一条，含它的完整演化链
    python -m oic.kb --selftest   断言六道闸真的会拦
"""

from __future__ import annotations

import sys
from pathlib import Path

from oic.kb.check import check_all
from oic.kb.index import write_index
from oic.kb.parse import EntryError, parse_entry
from oic.kb.schema import Band, Status
from oic.kb.store import load, repo_root_from


def _load(root: Path | None = None):
    return load(root or repo_root_from())


def cmd_check(root: Path | None = None) -> int:
    store = _load(root)
    report = check_all(store)
    print("\n".join(report.lines()))
    return 1 if report.errors else 0


def cmd_index(root: Path | None = None) -> int:
    store = _load(root)
    report = check_all(store)
    if report.errors:
        print("拒绝在有 ERROR 的状态下重建索引：")
        print("\n".join(f.line() for f in report.errors))
        return 1
    index_path, manifest_path = write_index(store)
    print(f"已重建 {index_path.name} 与 {manifest_path.name}"
          f"（{len(store.entries)} 条）")
    return 0


def cmd_stats(root: Path | None = None) -> int:
    store = _load(root)
    print(f"条目总数：{len(store.entries)}\n")
    for label, attribute in (("域", "domain"), ("类型", "type"),
                             ("成熟度", "maturity"), ("状态", "status")):
        print(f"按{label}：")
        for key, count in store.counts_by(attribute):
            print(f"  {key:<14} {count}")
        print()
    bands: dict[str, int] = {}
    for entry in store.entries:
        bands[entry.band] = bands.get(entry.band, 0) + 1
    print("按置信档位：")
    for band in (Band.CONFIRMED, Band.SUPPORTED, Band.PROVISIONAL,
                 Band.UNVERIFIED, Band.FALSIFIED):
        print(f"  {band:<12} {bands.get(band, 0)}")
    print()
    report = check_all(store)
    print(f"校验：{len(report.errors)} 错误 / {len(report.warnings)} 警告")
    return 0


def cmd_find(keyword: str, root: Path | None = None) -> int:
    store = _load(root)
    hits = [e for e in store.entries
            if keyword in e.title or keyword in e.body or keyword in e.id]
    if not hits:
        print(f"没有命中「{keyword}」")
        return 1
    for entry in hits:
        print(entry.one_line())
    print(f"\n共 {len(hits)} 条")
    return 0


def cmd_show(entry_id: str, root: Path | None = None) -> int:
    store = _load(root)
    entry = store.by_id.get(entry_id)
    if entry is None:
        print(f"没有这条：{entry_id}")
        return 1
    chain = store.chain(entry_id)
    print(entry.one_line())
    print(f"出处：{'、'.join(entry.sources)}")
    if len(chain) > 1:
        print("演化链：" + " → ".join(f"{e.id}(v{e.iteration})" for e in chain))
    if entry.superseded_by:
        print(f"⚠️ 已被 {entry.superseded_by} 取代")
    if entry.status == Status.FALSIFIED:
        print(f"❌ 已被 {entry.falsified_by} 推翻")
    print()
    print(entry.body)
    return 0


# ---------------------------------------------------------------------------
# 自检：证明六道闸真的会拦
# ---------------------------------------------------------------------------

_GOOD = """---
id: K-ACQ-999
title: 自检用条目
domain: acquisition
type: criterion
maturity: verified
status: active
evidence_grade: A
n_independent_sources: 1
sources:
  - oic/kb/schema.py
iteration: 1
---

## 断言
自检用。

## 依据
本文件。

## 边界
仅用于自检。
"""


def _selftest() -> int:
    failures = 0

    def check(label: str, ok: bool) -> None:
        nonlocal failures
        if not ok:
            failures += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    print("oic.kb 自检 —— 每条都在证明「这道闸真的会拦」\n")

    entry = parse_entry(_GOOD, "kb/entries/verified/acquisition/K-ACQ-999.md")
    check("合法条目能解析", entry.id == "K-ACQ-999")
    check("档位由证据推出而非手填", entry.band == Band.CONFIRMED)

    print("\n禁止手填置信度：")
    try:
        parse_entry(_GOOD.replace("iteration: 1", "confidence: 0.87\niteration: 1"))
        check("手填 confidence 被拒", False)
    except EntryError as exc:
        check("手填 confidence 被拒", "禁止字段" in str(exc))

    print("\n无出处即拒绝：")
    from oic.kb.schema import validate_fields
    from dataclasses import replace as _replace
    no_source = _replace(entry, sources=(), n_independent_sources=0)
    check("空 sources 被拒", any("没有出处" in p for p in validate_fields(no_source)))

    print("\n证伪必须留下推翻它的证据：")
    orphan = _replace(entry, status=Status.FALSIFIED)
    check("falsified 缺 falsified_by 被拒",
          any("falsified_by" in p for p in validate_fields(orphan)))

    print("\n边界是必填的：")
    no_boundary = _replace(entry, body="## 断言\nx\n\n## 依据\ny\n")
    check("缺「边界」小节被拒",
          any("边界" in p for p in validate_fields(no_boundary)))

    print("\nexternal 不得伪装成已验证：")
    from oic.kb.schema import Domain, Maturity
    fake = _replace(entry, id="K-EXT-999", domain=Domain.EXTERNAL,
                    maturity=Maturity.VERIFIED)
    check("external 分区标 verified 被拒",
          any("maturity 必须是 external" in p for p in validate_fields(fake)))

    print("\n实库校验：")
    store = load(repo_root_from())
    report = check_all(store)
    check(f"全库 {len(store.entries)} 条，0 ERROR", report.clean)

    print(f"\n{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    if "--check" in argv:
        return cmd_check()
    if "--index" in argv:
        return cmd_index()
    if "--stats" in argv:
        return cmd_stats()
    if "--find" in argv:
        i = argv.index("--find")
        if i + 1 >= len(argv):
            print("用法：--find <关键词>")
            return 2
        return cmd_find(argv[i + 1])
    if "--show" in argv:
        i = argv.index("--show")
        if i + 1 >= len(argv):
            print("用法：--show <条目 ID>")
            return 2
        return cmd_show(argv[i + 1])
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
