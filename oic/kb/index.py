"""索引生成 —— 确定性，零时钟，零 set 迭代。

## 为什么索引必须是确定性的

如果重跑一次索引就产生不同的字节，`git diff` 里永远有噪声，
真正的知识变更就会淹在噪声里。这是铁律 1（`verify_scores` 双跑一致）
在文档层的同一个道理。

**索引里不写生成时间。** 时间戳会让每次重建都产生 diff，
而「什么时候生成的」git 已经记录了。
"""

from __future__ import annotations

from pathlib import Path

from oic.kb.schema import (
    DOMAIN_CODES, Band, Domain, Entry, Maturity, Status,
)
from oic.kb.store import MANIFEST, Store, kb_dir

INDEX_FILE = "INDEX.md"

_DOMAIN_TITLES = {
    Domain.ACQUISITION: "取数与源治理",
    Domain.EVIDENCE: "证据核验",
    Domain.METRICS: "口径与时间闸",
    Domain.STATISTICS: "统计与防自欺",
    Domain.ANALYSIS: "商业分析引擎",
    Domain.COMPLIANCE: "法律与合规",
    Domain.ORCHESTRATION: "AI 调度体系",
    Domain.DELIVERY: "交付物",
    Domain.GOVERNANCE: "门禁 / 失效模式 / 回退规则",
    Domain.EXTERNAL: "通用 AI 方法论（本项目未验证）",
}

#: 域的展示顺序。固定顺序 = 可复现的索引。
_DOMAIN_ORDER = (
    Domain.GOVERNANCE, Domain.ORCHESTRATION, Domain.ACQUISITION,
    Domain.EVIDENCE, Domain.METRICS, Domain.STATISTICS,
    Domain.ANALYSIS, Domain.COMPLIANCE, Domain.DELIVERY, Domain.EXTERNAL,
)

_BAND_MARK = {
    Band.CONFIRMED: "✅",
    Band.SUPPORTED: "🟢",
    Band.PROVISIONAL: "🟡",
    Band.UNVERIFIED: "⬜",
    Band.FALSIFIED: "❌",
}


def _row(entry: Entry) -> str:
    link = f"[{entry.id}]({Path(entry.path).relative_to('kb').as_posix()})"
    flags = []
    if entry.status == Status.SUPERSEDED:
        flags.append(f"被 {entry.superseded_by} 取代")
    if entry.status == Status.FALSIFIED:
        flags.append(f"被 {entry.falsified_by} 推翻")
    if entry.iteration > 1:
        flags.append(f"v{entry.iteration}")
    note = "；".join(flags)
    return (f"| {link} | {entry.title} | {entry.type} | "
            f"{_BAND_MARK[entry.band]} {entry.band} | {note} |")


def render_index(store: Store) -> str:
    lines: list[str] = [
        "# 知识库索引",
        "",
        "> **本文件由 `python -m oic.kb --index` 生成，请勿手改。**",
        "> 手改的内容会在下次重建时被覆盖，而且不会有人发现。",
        "",
        f"共 **{len(store.entries)}** 条条目 · "
        f"现行 {len(store.active)} · "
        f"已被取代 {len(store.select(status=Status.SUPERSEDED))} · "
        f"已证伪 {len(store.falsified)} · "
        f"外部未验证 {len(store.external)}",
        "",
        "## 置信档位的含义",
        "",
        "| 档位 | 含义 |",
        "|---|---|",
        "| ✅ CONFIRMED | 关于世界：A 级证据 + ≥2 独立源 + 样本 ≥30；"
        "关于本系统：A 级证据且已验证 |",
        "| 🟢 SUPPORTED | 证据充分但未达上一档 |",
        "| 🟡 PROVISIONAL | 单源，或样本不足 |",
        "| ⬜ UNVERIFIED | 先验值，或外部来源 —— **本项目没有验证过** |",
        "| ❌ FALSIFIED | 已被后续证据推翻。**保留在库里**，因为「为什么错」是知识 |",
        "",
        "档位由 `(evidence_grade, n_independent_sources, sample_size, maturity)` "
        "确定性推出，**不可手填**。",
        "",
    ]

    for domain in _DOMAIN_ORDER:
        rows = [e for e in store.entries if e.domain == domain]
        if not rows:
            continue
        code = DOMAIN_CODES[domain]
        lines.append(f"## {code} · {_DOMAIN_TITLES[domain]}（{len(rows)} 条）")
        lines.append("")
        if domain == Domain.EXTERNAL:
            lines.append("> ⚠️ **这一区没有我们自己的验证。** 校验器强制它们"
                         "不得单独支撑任何已验证结论。")
            lines.append("")
        lines.append("| ID | 标题 | 类型 | 档位 | 备注 |")
        lines.append("|---|---|---|---|---|")
        lines.extend(_row(entry) for entry in rows)
        lines.append("")

    falsified = store.falsified
    if falsified:
        lines.append("## 已证伪清单（刻意保留）")
        lines.append("")
        lines.append("**被推翻的结论是资产。** 它记录了我们曾经怎么想、"
                     "被什么推翻、以及那次教训。删掉它等于让同一个错误可以再犯一次。")
        lines.append("")
        for entry in falsified:
            lines.append(f"- **{entry.id}** {entry.title} "
                         f"→ 被 `{entry.falsified_by}` 推翻")
        lines.append("")

    return "\n".join(lines) + "\n"


def render_manifest(store: Store) -> str:
    """号码本：只增不减。已发出的 id 永远留在这里。"""
    ids = sorted({e.id for e in store.entries} | set(store.known_ids))
    header = [
        "# 已发号清单 —— 只增不减",
        "# 条目文件可以改状态，但 id 一旦发出就永远登记在此。",
        "# 库里少了这里有的 id → `python -m oic.kb --check` 会报 ERROR。",
    ]
    return "\n".join(header + ids) + "\n"


def write_index(store: Store) -> tuple[Path, Path]:
    base = kb_dir(store.root)
    base.mkdir(parents=True, exist_ok=True)
    index_path = base / INDEX_FILE
    manifest_path = base / MANIFEST
    index_path.write_text(render_index(store), encoding="utf-8")
    manifest_path.write_text(render_manifest(store), encoding="utf-8")
    return index_path, manifest_path
