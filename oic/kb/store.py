"""全库加载 —— id 唯一性、链接图、已发号清单。

## 为什么需要一份「已发号清单」

「证伪不删除」这条规则，光靠 review 是守不住的：
删掉一个文件在 diff 里只是一行减号，很容易被放过去。

所以 `kb/IDS.txt` 是**只增不减**的号码本。
条目文件没了但号还在 → `check.py` 直接报 ERROR。
这让「删除」从一个安静的操作变成一个吵闹的操作。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping, Sequence

from oic.kb import KB_ROOT
from oic.kb.parse import EntryError, read_entry
from oic.kb.schema import Entry, Maturity, Status

#: 只增不减的号码本
MANIFEST = "IDS.txt"
PLAYBOOK_DIR = "playbooks"


@dataclass(frozen=True)
class Store:
    root: Path                              # 仓库根
    entries: tuple[Entry, ...]
    parse_errors: tuple[str, ...]
    known_ids: tuple[str, ...]              # IDS.txt 里的全部历史 id

    # -- 查询 ---------------------------------------------------------------

    @property
    def by_id(self) -> Mapping[str, Entry]:
        return {e.id: e for e in self.entries}

    def domain(self, domain: str) -> tuple[Entry, ...]:
        return tuple(e for e in self.entries if e.domain == domain)

    def select(self, domain: str | None = None, type: str | None = None,
               maturity: str | None = None, status: str | None = None,
               ) -> tuple[Entry, ...]:
        """按三轴过滤。全部为 None 即返回全库（已排序）。"""
        out = self.entries
        if domain is not None:
            out = tuple(e for e in out if e.domain == domain)
        if type is not None:
            out = tuple(e for e in out if e.type == type)
        if maturity is not None:
            out = tuple(e for e in out if e.maturity == maturity)
        if status is not None:
            out = tuple(e for e in out if e.status == status)
        return out

    @property
    def active(self) -> tuple[Entry, ...]:
        return tuple(e for e in self.entries if e.status == Status.ACTIVE)

    @property
    def falsified(self) -> tuple[Entry, ...]:
        """被推翻的知识。**这些是资产，不是垃圾** —— 它们记录了「为什么错」。"""
        return tuple(e for e in self.entries if e.status == Status.FALSIFIED)

    @property
    def external(self) -> tuple[Entry, ...]:
        return tuple(e for e in self.entries if e.maturity == Maturity.EXTERNAL)

    def chain(self, entry_id: str) -> tuple[Entry, ...]:
        """沿 supersedes 链回溯到最初版本，返回 [最早, …, 该条目]。

        这就是「可追溯」的具体含义：任何一条现行结论，
        都能一路看回它的前身以及每次改动的理由。
        """
        index = self.by_id
        out: list[Entry] = []
        seen: set[str] = set()
        cursor = index.get(entry_id)
        while cursor is not None and cursor.id not in seen:
            out.append(cursor)
            seen.add(cursor.id)
            cursor = index.get(cursor.supersedes) if cursor.supersedes else None
        return tuple(reversed(out))

    def current(self, entry_id: str) -> Entry | None:
        """顺 superseded_by 走到当前最新版本。"""
        index = self.by_id
        cursor = index.get(entry_id)
        seen: set[str] = set()
        while cursor is not None and cursor.superseded_by and cursor.id not in seen:
            seen.add(cursor.id)
            cursor = index.get(cursor.superseded_by)
        return cursor

    # -- 统计 ---------------------------------------------------------------

    def counts_by(self, attribute: str) -> tuple[tuple[str, int], ...]:
        tally: dict[str, int] = {}
        for entry in self.entries:
            key = str(getattr(entry, attribute))
            tally[key] = tally.get(key, 0) + 1
        return tuple(sorted(tally.items()))


def kb_dir(root: Path) -> Path:
    return root / KB_ROOT


def iter_entry_files(root: Path) -> Iterator[Path]:
    """确定性顺序遍历所有条目文件。**排序是必须的** ——
    未排序的目录遍历会让索引在不同机器上产生不同结果。"""
    base = kb_dir(root) / "entries"
    if not base.is_dir():
        return
    yield from sorted(base.rglob("*.md"))


def read_manifest(root: Path) -> tuple[str, ...]:
    path = kb_dir(root) / MANIFEST
    if not path.is_file():
        return ()
    lines = path.read_text(encoding="utf-8").splitlines()
    return tuple(line.strip() for line in lines
                 if line.strip() and not line.startswith("#"))


def load(root: Path) -> Store:
    """加载全库。解析失败的条目**不静默跳过**，而是收集成错误一并报出。"""
    entries: list[Entry] = []
    errors: list[str] = []
    for path in iter_entry_files(root):
        try:
            entries.append(read_entry(path, root))
        except EntryError as exc:
            errors.append(str(exc))
    entries.sort(key=lambda e: e.id)
    return Store(root=root, entries=tuple(entries), parse_errors=tuple(errors),
                 known_ids=read_manifest(root))


def iter_playbooks(root: Path) -> Iterator[Path]:
    base = kb_dir(root) / PLAYBOOK_DIR
    if not base.is_dir():
        return
    yield from sorted(base.glob("*.md"))


def repo_root_from(start: Path | None = None) -> Path:
    """从任意位置向上找到仓库根（含 `oic/` 与 `kb/` 的那一层）。"""
    cursor = (start or Path(__file__)).resolve()
    for candidate in [cursor] + list(cursor.parents):
        if (candidate / "oic").is_dir() and (candidate / KB_ROOT).is_dir():
            return candidate
    # 退化：包所在目录的上一级
    return Path(__file__).resolve().parents[2]


def sources_of(entries: Sequence[Entry]) -> tuple[str, ...]:
    seen: list[str] = []
    for entry in entries:
        for source in entry.sources:
            if source not in seen:
                seen.append(source)
    return tuple(sorted(seen))
