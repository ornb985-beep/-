"""front-matter 解析与写回 —— 纯标准库。

不引 PyYAML 是刻意的：整个仓库零第三方依赖，知识库没有理由成为第一个例外。
代价是只支持一个受限子集（标量 + 一层列表），而这恰好够用 ——
**条目的字段集是固定的，不需要通用 YAML 的表达力。**
"""

from __future__ import annotations

import re
from pathlib import Path

from oic.kb.schema import FORBIDDEN_FIELDS, Entry

DELIMITER = "---"

#: 标量字段
_SCALAR = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
#: 列表项（两空格缩进 + 短横线）
_ITEM = re.compile(r"^\s{2,}-\s+(.*)$")

#: 天然是列表的字段
LIST_FIELDS = ("sources", "tags")
#: 天然是整数的字段
INT_FIELDS = ("n_independent_sources", "sample_size", "iteration")


class EntryError(ValueError):
    """条目无法解析。**不返回半个条目** —— 半个条目会被下游当成完整的用。"""


def parse_entry(text: str, path: str = "") -> Entry:
    """把一份条目文件解析成 ``Entry``。"""
    where = f"{path}: " if path else ""
    lines = text.splitlines()

    if not lines or lines[0].strip() != DELIMITER:
        raise EntryError(f"{where}文件必须以 `---` 开头（front-matter 起始）")

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == DELIMITER:
            end = i
            break
    if end is None:
        raise EntryError(f"{where}front-matter 没有闭合的 `---`")

    fields: dict[str, object] = {}
    current_list: str | None = None

    for raw in lines[1:end]:
        if not raw.strip():
            continue
        item = _ITEM.match(raw)
        if item:
            if current_list is None:
                raise EntryError(f"{where}列表项「{item.group(1)}」没有所属字段")
            fields[current_list] = list(fields.get(current_list, [])) + [item.group(1).strip()]
            continue

        scalar = _SCALAR.match(raw)
        if not scalar:
            raise EntryError(f"{where}无法解析的 front-matter 行：{raw!r}")
        key, value = scalar.group(1), scalar.group(2).strip()

        # ② 置信度不可手填
        if key.lower() in FORBIDDEN_FIELDS:
            raise EntryError(
                f"{where}出现禁止字段「{key}」—— "
                "置信度由证据结构确定性推出，不允许手填。"
                "允许手填等于允许通胀：每个人都觉得自己那条挺可靠。"
            )

        if key in LIST_FIELDS:
            current_list = key
            fields.setdefault(key, [])
            if value:                      # 允许 `sources: a, b` 的行内写法
                fields[key] = [v.strip() for v in value.split(",") if v.strip()]
        else:
            current_list = None
            fields[key] = value

    body = "\n".join(lines[end + 1:]).strip()
    if not body:
        raise EntryError(f"{where}正文为空 —— 只有元数据的条目不承载知识")

    for key in INT_FIELDS:
        value = fields.get(key)
        if value in (None, ""):
            fields[key] = None if key == "sample_size" else (1 if key == "iteration" else 0)
            continue
        try:
            fields[key] = int(str(value))
        except ValueError as exc:
            raise EntryError(f"{where}{key} 必须是整数，实际「{value}」") from exc

    try:
        return Entry(
            id=str(fields.get("id", "")).strip(),
            title=str(fields.get("title", "")).strip(),
            domain=str(fields.get("domain", "")).strip(),
            type=str(fields.get("type", "")).strip(),
            maturity=str(fields.get("maturity", "")).strip(),
            status=str(fields.get("status", "active")).strip() or "active",
            evidence_grade=str(fields.get("evidence_grade", "")).strip(),
            n_independent_sources=int(fields.get("n_independent_sources") or 0),
            sample_size=fields.get("sample_size"),          # type: ignore[arg-type]
            sources=tuple(fields.get("sources") or ()),      # type: ignore[arg-type]
            supersedes=str(fields.get("supersedes", "")).strip(),
            superseded_by=str(fields.get("superseded_by", "")).strip(),
            falsified_by=str(fields.get("falsified_by", "")).strip(),
            iteration=int(fields.get("iteration") or 1),
            reviewed_on=str(fields.get("reviewed_on", "")).strip(),
            tags=tuple(fields.get("tags") or ()),             # type: ignore[arg-type]
            body=body,
            path=path,
        )
    except (TypeError, ValueError) as exc:
        raise EntryError(f"{where}字段类型错误：{exc}") from exc


def read_entry(path: Path, repo_root: Path) -> Entry:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EntryError(f"{path}: 读取失败 —— {exc}") from exc
    return parse_entry(text, path=str(path.relative_to(repo_root)))


#: 写回时的字段顺序。固定顺序 = 可复现的 diff。
FIELD_ORDER = (
    "id", "title", "domain", "type", "maturity", "status",
    "evidence_grade", "n_independent_sources", "sample_size",
    "sources", "tags", "supersedes", "superseded_by", "falsified_by",
    "iteration", "reviewed_on",
)


def render_entry(entry: Entry) -> str:
    """``Entry`` → 文件内容。字段顺序固定，保证同一条目重写后 diff 干净。"""
    out = [DELIMITER]
    values: dict[str, object] = {
        "id": entry.id, "title": entry.title, "domain": entry.domain,
        "type": entry.type, "maturity": entry.maturity, "status": entry.status,
        "evidence_grade": entry.evidence_grade,
        "n_independent_sources": entry.n_independent_sources,
        "sample_size": entry.sample_size, "sources": entry.sources,
        "tags": entry.tags, "supersedes": entry.supersedes,
        "superseded_by": entry.superseded_by, "falsified_by": entry.falsified_by,
        "iteration": entry.iteration, "reviewed_on": entry.reviewed_on,
    }
    for key in FIELD_ORDER:
        value = values[key]
        if key in LIST_FIELDS:
            out.append(f"{key}:")
            out.extend(f"  - {item}" for item in value or ())   # type: ignore[union-attr]
        elif value is None or value == "":
            out.append(f"{key}:")        # 空值不留尾随空格，保证 diff 干净
        else:
            out.append(f"{key}: {value}")
    out.append(DELIMITER)
    out.append("")
    out.append(entry.body.strip())
    out.append("")
    return "\n".join(out)
