"""演化 API —— 叠加进化的唯一合法入口。

## 只有两种演化，都不删除任何东西

    supersede(旧, 新)   我们有了更好的说法。旧条目留下，标 superseded，双向挂链。
    falsify(旧, 证据)   我们错了。旧条目留下，标 falsified，指向推翻它的证据。

**没有 delete。** 这不是疏漏 —— 删除会让「我们曾经这么认为」这段历史消失，
而那恰恰是知识库最值钱的部分：它让同一个错误不能再犯第二次。

真实案例：需求增速与结局的相关性，n=7 时 ρ=−0.289，我当时写了「方向值得记下来」。
n 翻倍到 11 后 ρ=+0.058、p=0.931，方向消失。如果当时直接删掉那段，
今天就没人知道「n=7 时哪怕方向讲得通也不能记」这条教训是怎么来的。
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from oic.kb.parse import render_entry
from oic.kb.schema import Entry, Maturity, Status, relative_dir, validate_fields
from oic.kb.store import Store, kb_dir

CHANGELOG = "CHANGELOG.md"


class EvolveError(RuntimeError):
    """演化操作不合法。**不静默降级** —— 半途而废的链比没有链更难查。"""


def entry_path(root: Path, entry: Entry) -> Path:
    return kb_dir(root) / relative_dir(entry.domain) / f"{entry.id}.md"


def _write(root: Path, entry: Entry) -> Path:
    problems = validate_fields(entry)
    if problems:
        raise EvolveError(f"{entry.id} 字段非法，拒绝写入：\n  " + "\n  ".join(problems))
    path = entry_path(root, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_entry(entry), encoding="utf-8")
    return path


def _append_changelog(root: Path, on: str, line: str) -> None:
    path = kb_dir(root) / CHANGELOG
    if not path.exists():
        path.write_text(
            "# 演化留痕\n\n"
            "> 由 `oic.kb.evolve` 自动追加。**只增不改** —— "
            "这份文件就是「什么时候、为什么改了主意」的全部答案。\n\n",
            encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"- `{on}` {line}\n")


def supersede(store: Store, old_id: str, new_entry: Entry,
              reason: str, on: str) -> tuple[Path, Path]:
    """用 ``new_entry`` 取代 ``old_id``。旧条目保留并标 superseded。

    ``on`` 是日期，由调用方传入 —— 本模块不读时钟，
    这样同一次演化在任何机器上重放都得到同样的文件。
    """
    old = store.by_id.get(old_id)
    if old is None:
        raise EvolveError(f"要取代的条目不存在：{old_id}")
    if old.status != Status.ACTIVE:
        raise EvolveError(
            f"{old_id} 当前状态为 {old.status}，不能被取代 —— "
            "只有现行条目才有「取代」的意义")
    if new_entry.id == old_id:
        raise EvolveError("新条目必须有新 id —— 原地覆盖会抹掉旧版本")
    if not reason.strip():
        raise EvolveError("必须写明取代理由 —— 没有理由的改动无法复审")

    updated_new = replace(
        new_entry,
        supersedes=old_id,
        iteration=max(old.iteration + 1, 2),
        status=Status.ACTIVE,
    )
    updated_old = replace(old, status=Status.SUPERSEDED, superseded_by=new_entry.id)

    new_path = _write(store.root, updated_new)
    old_path = _write(store.root, updated_old)
    _append_changelog(store.root, on,
                      f"**{new_entry.id}** 取代 {old_id}（v{updated_new.iteration}）：{reason}")
    return new_path, old_path


def falsify(store: Store, entry_id: str, falsified_by: str,
            reason: str, on: str) -> Path:
    """把某条标为已证伪。**内容原样保留。**

    ``falsified_by`` 必须是库里另一条真实存在的条目 ——
    「被什么推翻」本身也要有出处，否则只是换了一种说法的删除。
    """
    entry = store.by_id.get(entry_id)
    if entry is None:
        raise EvolveError(f"要证伪的条目不存在：{entry_id}")
    if falsified_by not in store.by_id:
        raise EvolveError(
            f"falsified_by 指向不存在的条目「{falsified_by}」—— "
            "「被什么推翻」必须能查到，否则等于没有说明")
    if entry_id == falsified_by:
        raise EvolveError("条目不能自己推翻自己")
    if not reason.strip():
        raise EvolveError("必须写明证伪理由 —— 这条理由就是这份知识的全部剩余价值")

    updated = replace(
        entry,
        status=Status.FALSIFIED,
        maturity=Maturity.FALSIFIED,
        falsified_by=falsified_by,
        body=entry.body.rstrip() + (
            f"\n\n## 已证伪\n\n"
            f"**{on} 被 `{falsified_by}` 推翻。** {reason}\n\n"
            f"原文以上内容原样保留 —— 删掉它等于让同一个错误可以再犯一次。\n"
        ),
    )
    path = _write(store.root, updated)
    _append_changelog(store.root, on,
                      f"❌ **{entry_id}** 被 {falsified_by} 推翻：{reason}")
    return path
