#!/usr/bin/env python3
# 把 .loop/ 和 docs/ 里的真实状态读成一个字典。
#
# 为什么单独抽出来：看板（静态 HTML）和面板（能点的界面）都要读同一批状态。
# 各写一份的话，迟早有一天两边显示的数字不一样，
# 而你没法知道哪个是真的——那比没有看板更糟。
#
# 这个文件只读，不写任何东西。

import os
import re
import glob
import subprocess

def rd(p, default=""):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return default

def rdl(p):
    return [x for x in rd(p).splitlines() if x.strip()]

STAGES = [("goal", "把想法变成目标"), ("giants", "站在巨人肩上"), ("edge", "共性与独特"),
          ("taste", "什么算好"), ("spec", "要做什么"), ("unknowns", "我不懂的"),
          ("stack", "技术与落地"), ("plan", "任务清单"), ("build", "自动开做"),
          ("done", "完成")]

# 这四步是生意问题，只有人能定。跟 loop.sh 的 stage_needs_signoff 必须一致。
SIGNOFF = {"edge", "taste", "spec", "stack"}

# 每一步产出哪份文档。跟 loop.sh 的 stage_doc 必须一致。
STAGE_DOC = {
    "goal": "00-目标.md", "giants": "01-巨人的肩膀.md", "edge": "02-共性与独特.md",
    "taste": "03-什么算好.md", "spec": "04-要做什么.md", "unknowns": "05-我不懂的.md",
    "stack": "06-技术与落地.md", "plan": "07-任务清单.md",
}

def _field(text, key):
    m = re.search(r"^%s(.+)$" % key, text, re.M)
    return m.group(1).strip() if m else ""

def _roles_in(root, d):
    L = os.path.join(root, ".loop")
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.md"))):
        n = os.path.basename(f)[:-3]
        t = rd(f)
        env = rd(f[:-3] + ".env")
        pv = _field(env, "LOOP_PROVIDER=")
        if env and not pv:
            pv = "自定义"
        logs = sorted(glob.glob(os.path.join(L, "log", "roles", n, "*.log")))
        out.append(dict(
            name=n,
            layer=_field(t, "层："),
            one=_field(t, "一句话："),
            typ=_field(t, "类型："),
            model=_field(t, "模型："),
            context=_field(t, "上下文："),
            provider=pv or "官方",
            switched=bool(pv),
            logs=len(logs),
            body=t,
        ))
    return out

def providers(root):
    """供应商表。唯一的真身在 lib.sh 里，这儿只是问它要。"""
    try:
        r = subprocess.run(
            ["bash", "-c", '. "$1/scripts/lib.sh"; provider_dump', "_", root],
            capture_output=True, text=True, timeout=10, cwd=root)
        rows = []
        for line in r.stdout.splitlines():
            p = line.split("|")
            if len(p) >= 6 and p[0]:
                rows.append(dict(code=p[0], name=p[1], url=p[2],
                                 big=p[3], small=p[4], verified=p[5]))
        return rows
    except Exception:
        return []

def read_all(root):
    L, D = os.path.join(root, ".loop"), os.path.join(root, "docs")

    stage = rd(os.path.join(L, "stage"), "goal").strip() or "goal"
    keys = [s for s, _ in STAGES]
    stage_i = keys.index(stage) if stage in keys else 0

    # ---------- 钱 ----------
    cost_rows, spent = [], 0.0
    for i, line in enumerate(rdl(os.path.join(L, "cost.tsv"))):
        if i == 0:
            continue
        p = line.split("\t")
        if len(p) >= 4:
            try:
                c = float(p[2])
            except ValueError:
                continue
            spent += c
            # 第5列是「这笔走的谁家接口」。老账单没这列，当官方。
            cost_rows.append(dict(time=p[0], who=p[1], cost=c, secs=p[3],
                                  provider=p[4] if len(p) >= 5 else "官方"))
    by_who = {}
    for r in cost_rows:
        by_who[r["who"]] = by_who.get(r["who"], 0) + r["cost"]

    # 走别家接口的那几笔，美元数是按官方价目表折算的，不是真花的钱。
    # 这个必须一路带到界面上，不然账面上就是一笔很正经的假账。
    off = {}
    for r in cost_rows:
        if r["provider"] and r["provider"] != "官方":
            off[r["provider"]] = off.get(r["provider"], 0) + 1

    budget = rd(os.path.join(L, "budget"), "").strip()

    # ---------- 人 ----------
    on = _roles_in(root, os.path.join(L, "roles"))
    arch = _roles_in(root, os.path.join(L, "封存"))
    pool_files = sorted(glob.glob(os.path.join(root, "roles-模板", "*.md")))
    pool = []
    for f in pool_files:
        t = rd(f)
        pool.append(dict(name=os.path.basename(f)[:-3],
                         layer=_field(t, "层："), one=_field(t, "一句话：")))
    on_names = {r["name"] for r in on}

    # ---------- 群聊 ----------
    chat = []
    for m in re.finditer(
            r"^\*\*(\d\d-\d\d \d\d:\d\d) · (.+?)\*\*\n+(.*?)(?=\n\*\*\d\d-\d\d |\Z)",
            rd(os.path.join(D, "10-群聊.md")), re.S | re.M):
        body = re.sub(r"^> ?", "", m.group(3).strip(), flags=re.M)
        chat.append(dict(time=m.group(1), who=m.group(2), body=body))

    # ---------- 派活台账 ----------
    tasks = []
    for i, line in enumerate(rdl(os.path.join(L, "tasks.tsv"))):
        if i == 0:
            continue
        p = line.split("\t")
        if len(p) >= 6:
            tasks.append(dict(id=p[0], who=p[1], what=p[2],
                              state=p[3], deliver=p[4], time=p[5]))

    # ---------- 项目任务清单 ----------
    tl = rd(os.path.join(D, "07-任务清单.md")).split("## 怎么验收")[0]
    todo = []
    for m in re.finditer(r"^\s*- \[([ xX])\] (.+)$", tl, re.M):
        text = m.group(2).strip()
        todo.append(dict(done=m.group(1).lower() == "x", text=text,
                         gated=bool(re.search(r"【需要你回答】|【停下来给我看】", text))))
    t_done = len([t for t in todo if t["done"]])
    t_open = len([t for t in todo if not t["done"]])
    t_gate = len([t for t in todo if not t["done"] and t["gated"]])

    # ---------- 标准修订（双环学习：标准本身有没有被改过） ----------
    rev = 0
    m = re.search(r"^##\s*标准修订记录(.*?)(?=^##\s|\Z)",
                  rd(os.path.join(D, "03-什么算好.md")), re.S | re.M)
    if m:
        rows = [r for r in m.group(1).splitlines() if r.strip().startswith("|")]
        rev = len([r for r in rows[2:] if re.sub(r"[|\s\-]", "", r)])

    # ---------- 九步 ----------
    steps = []
    for i, (k, label) in enumerate(STAGES):
        doc = STAGE_DOC.get(k, "")
        docpath = os.path.join(D, doc) if doc else ""
        steps.append(dict(
            key=k, label=label, n=i + 1,
            state="done" if i < stage_i else "now" if i == stage_i else "todo",
            signoff=k in SIGNOFF,
            signed=rd(os.path.join(L, "signoff_" + k), "no").strip() == "yes",
            ran=rd(os.path.join(L, "ran_" + k), "no").strip() == "yes",
            doc=doc,
            has_doc=bool(doc) and os.path.isfile(docpath),
        ))

    return dict(
        idea=rd(os.path.join(L, "原始想法.txt"), "").strip(),
        stage=stage, stage_index=stage_i, steps=steps,
        closed=rd(os.path.join(L, "closed"), "no").strip() == "yes",
        started=os.path.isdir(L) and bool(rd(os.path.join(L, "stage")).strip()),
        budget=budget, spent=round(spent, 4),
        cost_rows=cost_rows[-200:],
        by_who=sorted(by_who.items(), key=lambda x: -x[1]),
        off_providers=off,
        roles=on, archived=arch, pool=pool,
        not_hired=[p for p in pool if p["name"] not in on_names],
        chat=chat[-120:], tasks=tasks, todo=todo,
        todo_done=t_done, todo_open=t_open, todo_gate=t_gate,
        revisions=rev,
        providers=providers(root),
    )

def doc_text(root, name):
    """读 docs/ 下的一份文档。只许读 docs/ 和 references/，别的一律不给。"""
    base = os.path.realpath(root)
    for sub in ("docs", "references", "work"):
        p = os.path.realpath(os.path.join(base, sub, name))
        if p.startswith(os.path.join(base, sub) + os.sep) and os.path.isfile(p):
            return rd(p)
    return ""
