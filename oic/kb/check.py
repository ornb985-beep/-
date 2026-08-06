"""六条校验 —— 知识库和「一堆 markdown」的全部区别。

复用 `research/audit.py` 的 ``Finding``/``Severity`` 形状：
同一个仓库里，「检查出了问题」应当长成同一个样子。

| # | 规则 | 防的是什么 |
|---|---|---|
| ① | 无出处的条目不许存在，仓库内路径必须真实存在 | 说不出依据的结论 |
| ② | 置信度不可手填（在 `parse.py` 拦） | 置信度通胀 |
| ③ | external 不得单独支撑已验证结论 | 把「书上说」当成「我们测过」 |
| ④ | 证伪不删除，且必须留下推翻它的证据 | 「为什么错」永远查不到 |
| ⑤ | supersede 链双向一致、不成环 | 叠加进化断裂 |
| ⑥ | playbook 引用必须解析得到 | 复用变成脱钩的拷贝 |
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from oic.kb.schema import (
    EXTERNAL_SOURCE_PREFIX, Entry, Maturity, Status, validate_fields,
)
from oic.kb.store import Store, iter_playbooks

#: playbook 里对条目的引用写法：`[K-ACQ-001]`
REFERENCE = re.compile(r"\[(K-[A-Z]{3}-\d{3})\]")


class Severity:
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


@dataclass(frozen=True)
class Finding:
    severity: str
    check: str
    subject: str
    message: str

    def line(self) -> str:
        mark = {"ERROR": "🔴", "WARN": "⚠️", "INFO": "ℹ️"}[self.severity]
        return f"{mark} [{self.check}] {self.subject} —— {self.message}"


# ---------------------------------------------------------------------------
# ① 出处
# ---------------------------------------------------------------------------


def check_sources(store: Store) -> list[Finding]:
    """每条出处要么指向仓库里真实存在的文件，要么显式标为外部文献。

    「指向不存在的文件」比「没有出处」更危险 —— 它看起来是有依据的。
    """
    out: list[Finding] = []
    for entry in store.entries:
        for source in entry.sources:
            if source.startswith(EXTERNAL_SOURCE_PREFIX):
                if not source[len(EXTERNAL_SOURCE_PREFIX):].strip():
                    out.append(Finding(
                        Severity.ERROR, "sources", entry.id,
                        f"外部出处「{source}」没有内容"))
                continue
            target = source.split("#", 1)[0].split("::", 1)[0].strip()
            if not (store.root / target).exists():
                out.append(Finding(
                    Severity.ERROR, "sources", entry.id,
                    f"出处指向不存在的路径「{target}」—— "
                    "看起来有依据比没有依据更危险；"
                    f"外部文献请写成 `{EXTERNAL_SOURCE_PREFIX}<文献>`"))
    return out


# ---------------------------------------------------------------------------
# ② 字段（含禁止手填置信度，主拦截在 parse.py）
# ---------------------------------------------------------------------------


def check_fields(store: Store) -> list[Finding]:
    out = [Finding(Severity.ERROR, "parse", "—", message)
           for message in store.parse_errors]
    for entry in store.entries:
        for problem in validate_fields(entry):
            out.append(Finding(Severity.ERROR, "fields", entry.id, problem))
    return out


def check_unique_ids(store: Store) -> list[Finding]:
    seen: dict[str, str] = {}
    out: list[Finding] = []
    for entry in store.entries:
        if entry.id in seen:
            out.append(Finding(
                Severity.ERROR, "unique_id", entry.id,
                f"id 重复：{seen[entry.id]} 与 {entry.path}"))
        else:
            seen[entry.id] = entry.path
    return out


# ---------------------------------------------------------------------------
# ③ external 隔离
# ---------------------------------------------------------------------------


def check_external_isolation(store: Store) -> list[Finding]:
    """通用方法论可以收录，但**不得单独支撑一条已验证结论**。

    这是收录外部内容之后最关键的一道闸。没有它，
    「某篇博客这么说」和「我们跑了 30 个样本」会在同一张表里长得一模一样。
    """
    out: list[Finding] = []
    by_path = {e.path: e for e in store.entries}
    for entry in store.entries:
        if entry.maturity == Maturity.EXTERNAL:
            continue
        external_refs = []
        for source in entry.sources:
            target = by_path.get(source.split("#", 1)[0].strip())
            if target is not None and target.maturity == Maturity.EXTERNAL:
                external_refs.append(target.id)
        if external_refs and len(external_refs) == len(entry.sources):
            out.append(Finding(
                Severity.ERROR, "external_isolation", entry.id,
                f"唯一依据是 external 条目 {external_refs} —— "
                "未经本项目验证的内容不得单独支撑已验证结论；"
                "请补一条本仓库的代码/测试/实测出处，或把本条改为 external"))
    return out


# ---------------------------------------------------------------------------
# ④ 证伪不删除
# ---------------------------------------------------------------------------


def check_no_deletion(store: Store) -> list[Finding]:
    """号码本里有、库里没有 → 有人删了条目。

    删除让「我们曾经这么认为，后来被推翻」这段历史消失，
    而那恰恰是知识库最值钱的部分。
    """
    present = {e.id for e in store.entries}
    out: list[Finding] = []
    for known in store.known_ids:
        if known not in present:
            out.append(Finding(
                Severity.ERROR, "no_deletion", known,
                "该 id 在 kb/IDS.txt 里登记过，但库中已不存在 —— "
                "证伪与取代都不删除条目，改状态即可"))
    for entry in store.entries:
        if store.known_ids and entry.id not in store.known_ids:
            out.append(Finding(
                Severity.WARN, "no_deletion", entry.id,
                "新条目未登记进 kb/IDS.txt —— 请运行 `python -m oic.kb --index`"))
    return out


# ---------------------------------------------------------------------------
# ⑤ 链完整性
# ---------------------------------------------------------------------------


def check_links(store: Store) -> list[Finding]:
    index = store.by_id
    out: list[Finding] = []

    for entry in store.entries:
        for field_name, target_id in (("supersedes", entry.supersedes),
                                      ("superseded_by", entry.superseded_by),
                                      ("falsified_by", entry.falsified_by)):
            if not target_id:
                continue
            target = index.get(target_id)
            if target is None:
                out.append(Finding(
                    Severity.ERROR, "links", entry.id,
                    f"{field_name} 指向不存在的条目「{target_id}」"))
                continue
            if field_name == "supersedes" and target.superseded_by != entry.id:
                out.append(Finding(
                    Severity.ERROR, "links", entry.id,
                    f"单向链：{entry.id} 声称取代 {target_id}，"
                    f"但 {target_id}.superseded_by = 「{target.superseded_by}」"))
            if field_name == "supersedes" and target.status == Status.ACTIVE:
                out.append(Finding(
                    Severity.ERROR, "links", target_id,
                    f"已被 {entry.id} 取代却仍是 active —— 状态应为 superseded"))

    # 成环检测
    for entry in store.entries:
        seen: set[str] = set()
        cursor: Entry | None = entry
        while cursor is not None and cursor.supersedes:
            if cursor.supersedes in seen:
                out.append(Finding(
                    Severity.ERROR, "links", entry.id,
                    f"supersede 链成环，经过「{cursor.supersedes}」"))
                break
            seen.add(cursor.supersedes)
            cursor = index.get(cursor.supersedes)
    return out


# ---------------------------------------------------------------------------
# ⑥ playbook 引用
# ---------------------------------------------------------------------------


#: 引用一条非现行条目时，同一行必须出现下列任一措辞，
#: 以证明作者知道它已经不作数了。
_STATUS_ACKNOWLEDGED = ("FALSIFIED", "证伪", "推翻", "已被取代", "superseded", "SUPERSEDED")


def check_playbooks(store: Store) -> list[Finding]:
    """playbook 靠引用复用条目，不靠拷贝。断链即失效。

    引用已证伪/已取代的条目**不一定是错** —— 讲教训时就该指向那条。
    但作者必须在同一行写明它的状态，否则读者会把它当成现行结论。
    要求「同一行」而不是「同一篇」，是因为读者是按行读的。

    这条规则刻意不做成永久警告：**长期挂着的警告会训练人忽略警告**，
    那正是 K-GOV-013（污染检测误报多于真报）描述的失效模式。
    """
    index = store.by_id
    out: list[Finding] = []
    for path in iter_playbooks(store.root):
        text = path.read_text(encoding="utf-8")
        name = str(path.relative_to(store.root))
        if not REFERENCE.search(text):
            out.append(Finding(
                Severity.WARN, "playbook", name,
                "没有引用任何条目 —— playbook 应当引用条目而不是复述内容"))
        for lineno, line in enumerate(text.splitlines(), start=1):
            for ref in REFERENCE.findall(line):
                target = index.get(ref)
                if target is None:
                    out.append(Finding(
                        Severity.ERROR, "playbook", f"{name}:{lineno}",
                        f"引用了不存在的条目「{ref}」"))
                    continue
                if target.status == Status.ACTIVE:
                    continue
                if any(mark in line for mark in _STATUS_ACKNOWLEDGED):
                    continue                   # 作者已在同一行标明状态
                out.append(Finding(
                    Severity.ERROR, "playbook", f"{name}:{lineno}",
                    f"引用的 {ref} 状态为 {target.status}，但本行未标明 —— "
                    f"读者会把它当成现行结论。"
                    f"要么改引 {target.superseded_by or target.falsified_by or '新版本'}，"
                    f"要么在同一行写明它已被推翻/取代"))
    return out


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------

ALL_CHECKS = (
    ("fields", check_fields),
    ("unique_id", check_unique_ids),
    ("sources", check_sources),
    ("external_isolation", check_external_isolation),
    ("no_deletion", check_no_deletion),
    ("links", check_links),
    ("playbook", check_playbooks),
)


@dataclass(frozen=True)
class CheckReport:
    findings: tuple[Finding, ...]
    n_entries: int

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == Severity.WARN)

    @property
    def clean(self) -> bool:
        return not self.errors

    def lines(self) -> tuple[str, ...]:
        out = [f"校验 {self.n_entries} 条条目："
               f"{len(self.errors)} 个错误、{len(self.warnings)} 个警告"]
        out.extend(f.line() for f in self.findings)
        if self.clean and not self.warnings:
            out.append("✅ 六条校验全部通过")
        return tuple(out)


def check_all(store: Store) -> CheckReport:
    findings: list[Finding] = []
    for _, check in ALL_CHECKS:
        findings.extend(check(store))
    order = {Severity.ERROR: 0, Severity.WARN: 1, Severity.INFO: 2}
    findings.sort(key=lambda f: (order[f.severity], f.check, f.subject, f.message))
    return CheckReport(tuple(findings), len(store.entries))
