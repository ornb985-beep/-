#!/usr/bin/env python3
# 从真实状态生成一个本地看板 HTML。
#
# 为什么是本地 HTML 不是网页服务：这套东西是你机器上的一个脚本，
# 没有常驻服务。生成一个自包含的 .html，双击就开，
# 想刷新就再跑一次 ./loop.sh 看板。零依赖、断网能用、不会挂。
#
# 它只读，不写任何状态——看板坏了不影响 loop 跑。

import os, re, sys, html, glob, datetime

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
L, D = os.path.join(ROOT, ".loop"), os.path.join(ROOT, "docs")

def rd(p, default=""):
    try:
        with open(p, encoding="utf-8") as f: return f.read()
    except Exception: return default

def rdl(p):
    return [x for x in rd(p).splitlines() if x.strip()]

STAGES = [("goal","把想法变成目标"),("giants","站在巨人肩上"),("edge","共性与独特"),
          ("taste","什么算好"),("spec","要做什么"),("unknowns","我不懂的"),
          ("stack","技术与落地"),("plan","任务清单"),("build","自动开做"),("done","完成")]

stage = rd(os.path.join(L,"stage"),"goal").strip() or "goal"
idea  = rd(os.path.join(L,"原始想法.txt"),"（还没开始）").strip()
budget= rd(os.path.join(L,"budget"),"").strip()
closed= rd(os.path.join(L,"closed"),"no").strip() == "yes"

# ---------- 钱 ----------
cost_rows, spent = [], 0.0
for i, line in enumerate(rdl(os.path.join(L,"cost.tsv"))):
    if i == 0: continue
    p = line.split("\t")
    if len(p) >= 4:
        try: c = float(p[2])
        except ValueError: continue
        spent += c
        cost_rows.append((p[0], p[1], c, p[3]))
by_who = {}
for _, who, c, _s in cost_rows:
    by_who[who] = by_who.get(who, 0) + c
top_cost = sorted(by_who.items(), key=lambda x: -x[1])[:8]

# ---------- 人 ----------
def roles_in(d):
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.md"))):
        n = os.path.basename(f)[:-3]
        t = rd(f)
        layer = (re.search(r"^层：(.+)$", t, re.M) or [None,""])[1].strip() if re.search(r"^层：", t, re.M) else ""
        one   = (re.search(r"^一句话：(.+)$", t, re.M) or [None,""])[1].strip() if re.search(r"^一句话：", t, re.M) else ""
        typ   = (re.search(r"^类型：(.+)$", t, re.M) or [None,""])[1].strip() if re.search(r"^类型：", t, re.M) else ""
        model = (re.search(r"^模型：(.+)$", t, re.M) or [None,""])[1].strip() if re.search(r"^模型：", t, re.M) else ""
        logs  = len(glob.glob(os.path.join(L,"log","roles",n,"*.log")))
        out.append(dict(name=n, layer=layer, one=one, typ=typ, model=model, logs=logs))
    return out

on   = roles_in(os.path.join(L,"roles"))
arch = roles_in(os.path.join(L,"封存"))
pool = [os.path.basename(f)[:-3] for f in sorted(glob.glob(os.path.join(ROOT,"roles-模板","*.md")))]
on_names = {r["name"] for r in on}

def group(rs, layer): return [r for r in rs if r["layer"] == layer]
staff_adv  = group(on,"参谋")
staff_exec = group(on,"执行")
staff_dist = group(on,"蒸馏")
not_hired  = [p for p in pool if p not in on_names]

# ---------- 群聊 ----------
chat = []
for m in re.finditer(r"^\*\*(\d\d-\d\d \d\d:\d\d) · (.+?)\*\*\n+(.*?)(?=\n\*\*\d\d-\d\d |\Z)",
                     rd(os.path.join(D,"10-群聊.md")), re.S|re.M):
    body = m.group(3).strip()
    body = re.sub(r"^> ?", "", body, flags=re.M)
    chat.append((m.group(1), m.group(2), body))
chat = chat[-40:]

# ---------- 台账 ----------
tasks = []
for i, line in enumerate(rdl(os.path.join(L,"tasks.tsv"))):
    if i == 0: continue
    p = line.split("\t")
    if len(p) >= 6: tasks.append(p)

# ---------- 项目任务清单 ----------
tl = rd(os.path.join(D,"07-任务清单.md"))
tl = tl.split("## 怎么验收")[0]
t_done = len(re.findall(r"^\s*- \[[xX]\] ", tl, re.M))
t_open = len(re.findall(r"^\s*- \[ \] ", tl, re.M))
t_gate = len(re.findall(r"^\s*- \[ \] .*(【需要你回答】|【停下来给我看】)", tl, re.M))

# ---------- 标准修订 ----------
rev = 0
m = re.search(r"^##\s*标准修订记录(.*?)(?=^##\s|\Z)", rd(os.path.join(D,"03-什么算好.md")), re.S|re.M)
if m:
    rows = [r for r in m.group(1).splitlines() if r.strip().startswith("|")]
    rev = len([r for r in rows[2:] if re.sub(r"[|\s\-]", "", r)])

e = html.escape
def pct(a,b): return 0 if not b else round(a*100/b)

def person(r, extra=""):
    tag = f'<span class="t">{e(r["typ"])}</span>' if r["typ"] else ""
    mdl = f'<span class="m">{e(r["model"])}</span>' if r["model"] else ""
    n = f'<span class="n">{r["logs"]}</span>' if r["logs"] else ""
    return (f'<div class="p {extra}"><div class="ph"><b>{e(r["name"])}</b>{tag}{mdl}{n}</div>'
            f'<div class="po">{e(r["one"])}</div></div>')

stage_i = [s for s,_ in STAGES].index(stage) if stage in [s for s,_ in STAGES] else 0
steps = "".join(
    f'<div class="st {"done" if i<stage_i else "now" if i==stage_i else ""}">'
    f'<i>{i+1 if i<9 else "✓"}</i><span>{e(t)}</span></div>'
    for i,(s,t) in enumerate(STAGES))

chat_html = "".join(
    f'<div class="msg {"me" if w=="你" or w.startswith("你 ") else "sys" if w=="系统" else "ceo" if "CEO" in w else ""}">'
    f'<div class="mh"><b>{e(w)}</b><time>{e(t)}</time></div>'
    f'<div class="mb">{e(b[:700])}{"…" if len(b)>700 else ""}</div></div>'
    for t,w,b in reversed(chat)) or '<p class="empty">还没有人说话。<code>./loop.sh say "话"</code></p>'

task_html = "".join(
    f'<tr><td class="num">#{e(t[0])}</td><td>{e(t[1])}</td>'
    f'<td><span class="badge b{"ok" if t[3]=="干完了" else "no" if t[3]=="没交东西" else "run"}">{e(t[3])}</span></td>'
    f'<td class="dim">{e(t[2][:46])}</td></tr>' for t in reversed(tasks)) or \
    '<tr><td colspan="4" class="empty">还没派过活</td></tr>'

cost_html = "".join(
    f'<tr><td>{e(w)}</td><td class="num">${c:.2f}</td>'
    f'<td class="bar"><i style="width:{pct(c, top_cost[0][1])}%"></i></td></tr>'
    for w,c in top_cost) or '<tr><td colspan="3" class="empty">还没花钱</td></tr>'

bud = f'{spent:.2f} / {budget}' if budget else f'{spent:.2f}（没设上限）'
bud_pct = pct(spent, float(budget)) if budget else 0

HTML = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MoneyLoop 看板</title><style>
*{{box-sizing:border-box}}
:root{{--bg:#0d141b;--card:#141f29;--card2:#1b2934;--ink:#e3ebf2;--ink2:#9fb2c0;--ink3:#6b8095;
--line:#233343;--blue:#5aa3d8;--ok:#4fb98a;--warn:#d9a05b;--bad:#d4705f;--purple:#9b8ad4}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 "PingFang SC","Noto Sans SC","Microsoft YaHei",system-ui,sans-serif}}
.wrap{{max-width:1500px;margin:0 auto;padding:22px}}
h1{{font-size:22px;margin:0 0 4px}} h1 small{{color:var(--ink3);font-weight:400;font-size:14px;margin-left:10px}}
.idea{{color:var(--ink2);margin:0 0 18px;font-size:14.5px}}
.grid{{display:grid;grid-template-columns:300px 1fr 340px;gap:16px;align-items:start}}
@media(max-width:1200px){{.grid{{grid-template-columns:1fr}}}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px}}
.card h2{{font-size:13px;margin:0 0 12px;color:var(--ink3);letter-spacing:.06em;font-weight:600}}
.steps{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:16px}}
.st{{flex:1;min-width:88px;background:var(--card);border:1px solid var(--line);border-radius:7px;padding:8px 9px;font-size:12px;color:var(--ink3)}}
.st i{{display:block;font-style:normal;font-size:11px;opacity:.6}}
.st.done{{border-color:#2b5c48;color:var(--ok)}} .st.done i{{color:var(--ok)}}
.st.now{{border-color:var(--blue);background:#12293a;color:var(--ink)}} .st.now i{{color:var(--blue)}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:16px}}
.k{{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px 14px}}
.k b{{display:block;font-size:23px;line-height:1.2;font-variant-numeric:tabular-nums}}
.k span{{font-size:12px;color:var(--ink3)}}
.k.ok b{{color:var(--ok)}} .k.warn b{{color:var(--warn)}} .k.blue b{{color:var(--blue)}}
.prog{{height:5px;background:var(--card2);border-radius:3px;margin-top:8px;overflow:hidden}}
.prog i{{display:block;height:100%;background:var(--blue)}}
.prog.hot i{{background:var(--bad)}}
.lay{{font-size:11.5px;color:var(--ink3);margin:14px 0 7px;letter-spacing:.05em}}
.lay:first-child{{margin-top:0}}
.p{{background:var(--card2);border-radius:7px;padding:8px 10px;margin-bottom:5px;border-left:2px solid var(--line)}}
.p.adv{{border-left-color:var(--blue)}} .p.exe{{border-left-color:var(--warn)}} .p.dis{{border-left-color:var(--purple)}}
.p.arc{{opacity:.45}}
.ph{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}} .ph b{{font-size:13.5px}}
.po{{font-size:11.5px;color:var(--ink3);margin-top:1px;line-height:1.45}}
.t,.m,.n{{font-size:10px;padding:1px 5px;border-radius:3px}}
.t{{background:#1d3547;color:var(--blue)}} .m{{background:#2a2340;color:var(--purple)}}
.n{{background:var(--line);color:var(--ink3);margin-left:auto}}
.pool{{font-size:12px;color:var(--ink3);line-height:1.9}}
.pool code{{background:var(--card2);padding:1px 5px;border-radius:3px;color:var(--ink2)}}
.msg{{border-bottom:1px solid var(--line);padding:11px 0}} .msg:last-child{{border:0}}
.mh{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px}}
.mh b{{font-size:13px;color:var(--blue)}} .mh time{{font-size:11px;color:var(--ink3)}}
.msg.me .mh b{{color:var(--ok)}} .msg.ceo .mh b{{color:var(--warn)}} .msg.sys .mh b{{color:var(--ink3)}}
.mb{{font-size:13px;color:var(--ink2);white-space:pre-wrap;word-break:break-word;max-height:190px;overflow:auto}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}
td{{padding:6px 5px;border-bottom:1px solid var(--line);vertical-align:top}}
.num{{font-variant-numeric:tabular-nums;color:var(--ink3);white-space:nowrap}}
.dim{{color:var(--ink3)}}
.badge{{font-size:11px;padding:1px 6px;border-radius:3px;white-space:nowrap}}
.bok{{background:#16362a;color:var(--ok)}} .bno{{background:#3a2320;color:var(--bad)}} .brun{{background:#1d3547;color:var(--blue)}}
.bar{{width:74px}} .bar i{{display:block;height:6px;background:var(--blue);border-radius:3px}}
.empty{{color:var(--ink3);font-size:12.5px;text-align:center;padding:14px 0}}
.foot{{color:var(--ink3);font-size:12px;margin-top:18px;border-top:1px solid var(--line);padding-top:14px}}
.foot code{{background:var(--card2);padding:1px 6px;border-radius:3px;color:var(--ink2)}}
.closed{{background:#3a2320;border-color:var(--bad);color:var(--bad);padding:10px 14px;border-radius:8px;margin-bottom:16px;font-size:13.5px}}
</style></head><body><div class="wrap">

<h1>MoneyLoop 看板 <small>{datetime.datetime.now():%Y-%m-%d %H:%M} 生成</small></h1>
<p class="idea">{e(idea[:200])}</p>
{'<div class="closed">这个项目已结项。复盘在 docs/99-结项.md</div>' if closed else ''}

<div class="steps">{steps}</div>

<div class="kpi">
  <div class="k blue"><b>{t_done}/{t_done+t_open}</b><span>项目任务做完</span>
    <div class="prog"><i style="width:{pct(t_done,t_done+t_open)}%"></i></div></div>
  <div class="k warn"><b>{t_gate}</b><span>只有你能干的</span></div>
  <div class="k"><b>{len(on)}</b><span>在岗 · 封存 {len(arch)}</span></div>
  <div class="k {'warn' if bud_pct>=80 else 'ok'}"><b>${bud}</b><span>花了 / 上限</span>
    {f'<div class="prog {"hot" if bud_pct>=80 else ""}"><i style="width:{min(bud_pct,100)}%"></i></div>' if budget else ''}</div>
  <div class="k {'ok' if rev else 'warn'}"><b>{rev}</b><span>标准改过几次</span></div>
</div>

<div class="grid">
  <div>
    <div class="card">
      <h2>组织 · 你 → CEO → 两个分支</h2>
      <div class="lay">左分支 · 参谋层（只出意见）</div>
      {"".join(person(r,"adv") for r in staff_adv) or '<p class="empty">还没招</p>'}
      <div class="lay">右分支 · 执行层（干活交付）</div>
      {"".join(person(r,"exe") for r in staff_exec) or '<p class="empty">还没招</p>'}
      {'<div class="lay">蒸馏专家（真人的公开材料）</div>' + "".join(person(r,"dis") for r in staff_dist) if staff_dist else ''}
      {'<div class="lay">已封存（随时起复）</div>' + "".join(person(r,"arc") for r in arch) if arch else ''}
    </div>
    {f'<div class="card"><h2>还没招的</h2><p class="pool">{"、".join(e(p) for p in not_hired)}<br><code>./loop.sh hire 名字</code></p></div>' if not_hired else ''}
  </div>

  <div class="card">
    <h2>群聊 · 最近 {len(chat)} 条（新的在上）</h2>
    {chat_html}
  </div>

  <div>
    <div class="card"><h2>派活台账</h2><table>{task_html}</table></div>
    <div class="card"><h2>钱花在谁身上（共 ${spent:.2f} / {len(cost_rows)} 次）</h2><table>{cost_html}</table></div>
  </div>
</div>

<p class="foot">这个看板只读状态，不改任何东西——它坏了不影响 loop 跑。<br>
想刷新就再跑一次 <code>./loop.sh 看板</code>。跟 CEO 说话：<code>./loop.sh say "你的话"</code></p>
</div></body></html>"""

out = os.path.join(ROOT, "看板.html")
with open(out, "w", encoding="utf-8") as f: f.write(HTML)
print(out)
