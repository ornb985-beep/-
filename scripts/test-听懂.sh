#!/usr/bin/env bash
# 第1步「听懂」的自测。不花钱、不联网。
#
# 这一步跟别的步不一样，它是【引导式】的：可能问你好几轮，你答完它再听一遍。
# 所以最坏的失败方式不是报错，是两种"看起来对"：
#   ① 它其实没听懂，却往下走了 → 后面八步全建立在一个误解上
#   ② 它一直说没听懂，问个没完 → 你被困在第1步
# 这里两头都测。
#
# 还有一件事必须守住：十步的清单被抄了三份（lib.sh / 状态.py / 看板.py）。
# 抄的东西会漂。漂了的话界面上的进度、拍板闸门、文档名全是错的，
# 而且【看不出来是错的】。第一节就是逐项对着比。

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }
check() {
  if [ "$2" = "$3" ]; then pass "$1"
  else fail "$1"; printf '         期望：%s\n         实际：%s\n' "$2" "$3"; fi
}

echo
echo "=== 第1步「听懂」自测 ==="

# ---------- 一、三份拷贝不许漂 ----------
drift="$(python3 - "$REPO" <<'PY'
import subprocess, sys, os
repo = sys.argv[1]
sys.path.insert(0, os.path.join(repo, "scripts"))
import 状态 as ST

def bash(snippet):
    r = subprocess.run(["bash", "-c", '. "$1/scripts/lib.sh"; ' + snippet, "_", repo],
                       capture_output=True, text=True, cwd=repo)
    return r.stdout.strip()

bad = []

# STAGES 顺序
want = bash('printf "%s\\n" "${STAGES[@]}"').split()
got  = [k for k, _ in ST.STAGES]
if want != got:
    bad.append("STAGES 不一致\n  lib.sh: %s\n  状态.py: %s" % (want, got))

# 哪些步要人拍板
for k in want:
    b = bash('stage_needs_signoff "%s" && echo yes || echo no' % k) == "yes"
    p = k in ST.SIGNOFF
    if b != p:
        bad.append("要不要拍板对不上：%s（lib.sh=%s 状态.py=%s）" % (k, b, p))

# 每步产出哪份文档
for k in want:
    b = os.path.basename(bash('stage_doc "%s"' % k))
    p = ST.STAGE_DOC.get(k, "")
    if b != p:
        bad.append("产出文档对不上：%s（lib.sh=%r 状态.py=%r）" % (k, b, p))

# 看板不许再自己抄一份
import pathlib
kb = pathlib.Path(repo, "scripts", "看板.py").read_text(encoding="utf-8")
if "STAGES = [" in kb:
    bad.append("看板.py 又自己抄了一份 STAGES —— 必须 from 状态 import")

print("\n".join(bad))
PY
)"
if [ -z "$drift" ]; then
  pass "十步清单三处一致（lib.sh / 状态.py / 看板.py）"
else
  fail "十步清单漂了"; printf '%s\n' "$drift" | sed 's/^/         /'
fi

# 每份说明书开头写的「第N步」，得跟它在流程里的真实位置一样。
#
# 为什么单测这条：references/框架库.md 里「第4步『要做什么』」这个错，
# 挂了很久没人发现——因为没有任何人、任何东西会去核对编号。
# 插一个新步骤就会让所有编号错位一格，而且错了完全看不出来。
badnum=""
for st in $(bash -c '. "$1/scripts/lib.sh"; printf "%s\n" "${STAGES[@]}"' _ "$REPO"); do
  [ "$st" = "done" ] && continue
  f="$REPO/.claude/commands/$st.md"
  [ -f "$f" ] || { badnum="$badnum
  $st 没有说明书文件"; continue; }
  want="$(bash -c '. "$1/scripts/lib.sh"; stage_num "$2"' _ "$REPO" "$st")"
  got="$(grep -m1 -oE '^description: 第[0-9]+步' "$f" | grep -oE '[0-9]+' || true)"
  [ "$want" = "$got" ] || badnum="$badnum
  $st.md 写着第${got:-?}步，实际是第${want}步"
done
if [ -z "$badnum" ]; then
  pass "十份说明书开头的「第N步」都对得上真实位置"
else
  fail "说明书的步骤编号对不上"; printf '%s\n' "$badnum"
fi

# ---------- 搭个沙盘，用假的 claude ----------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
SANDBOX="$TMP/sandbox"
mkdir -p "$SANDBOX"
cp "$REPO/loop.sh" "$SANDBOX/"
cp -r "$REPO/scripts" "$REPO/.claude" "$SANDBOX/"
rm -rf "$SANDBOX/scripts/__pycache__"
chmod +x "$SANDBOX/loop.sh"

# 假 claude：把「这一轮该写什么」从环境变量里拿，写进 docs/00-听到的.md
mkdir -p "$TMP/bin"
cat > "$TMP/bin/claude" <<'FAKE'
#!/usr/bin/env bash
cat > /dev/null
if [ -n "${FAKE_WRITE:-}" ]; then
  mkdir -p "$(dirname "$FAKE_WRITE")"
  printf '%s\n' "${FAKE_BODY:-}" > "$FAKE_WRITE"
fi
echo '{"result":"假的回答","total_cost_usd":0.01,"duration_ms":900}'
FAKE
chmod +x "$TMP/bin/claude"
export CLAUDE_BIN="$TMP/bin/claude"
export FAKE_WRITE="$SANDBOX/docs/00-听到的.md"

listen_doc() { cat "$SANDBOX/docs/00-听到的.md" 2>/dev/null; }
stage_now()  { cat "$SANDBOX/.loop/stage" 2>/dev/null; }

# ---------- 二、start 之后应该停在第1步 ----------
export FAKE_BODY='# 00 · 我听到的

原话：「我想做个帮我记客户跟进的小工具」

轮次：第 1 轮   状态：还没听懂

## 四、我不许替你猜的

### 问题 1：你现在有多少个客户要跟
- **A** 50 个以内，一个人管得过来
- **B** 几百个，得靠工具
- **我推荐 A**，因为你说的是"小工具"

## 五、我可能听错的地方
1. 也许你要的不是记录，是提醒'
( cd "$SANDBOX" && ./loop.sh start "我想做个帮我记客户跟进的小工具" >/dev/null 2>&1 )
check "start 之后停在第1步「听懂」" "听懂" "$(stage_now)"
[ -f "$SANDBOX/docs/00-听到的.md" ] \
  && pass "产出了 docs/00-听到的.md" || fail "没产出 docs/00-听到的.md"

# ---------- 三、还没听懂就不许往下走 ----------
( cd "$SANDBOX" && ./loop.sh go >/dev/null 2>&1 )
check "「还没听懂」时，go 不会溜到第2步" "听懂" "$(stage_now)"

out="$( cd "$SANDBOX" && ./loop.sh go 2>&1 )"
printf '%s' "$out" | grep -q "问题 1" \
  && pass "它把问题直接打在屏幕上（不用你翻文件）" \
  || fail "问题没打出来，人得自己去翻文件找"

# ---------- 四、答一句，轮次要往前走 ----------
( cd "$SANDBOX" && FAKE_WRITE="" ./loop.sh 答 "1A，其实我最烦的是老忘了谁该回访" >/dev/null 2>&1 )
listen_doc | grep -q "老忘了谁该回访" \
  && pass "回答被记进了文档" || fail "回答没进文档"
listen_doc | grep -q "## 你的回答" \
  && pass "回答单独成节，看得出是你说的" || fail "回答没有单独成节"

# ---------- 五、说听懂了，才准进第1步 ----------
export FAKE_BODY='# 00 · 我听到的

原话：「我想做个帮我记客户跟进的小工具」

轮次：第 2 轮   状态：听懂了

## 三、我推断你真正要的
真实痛点：老忘了谁该回访 [推断，依据：你原话里的"记客户跟进"]'
# 注意：这里必须用「答」而不是「go」。
# 还没听懂的时候 go 只重显问题、不重跑（重跑要花钱，而你没给新信息）。
# 要往前推进只有一条路：答一句。这条本身就是在验证那个设计。
( cd "$SANDBOX" && ./loop.sh 答 "B，几百个" >/dev/null 2>&1 )
listen_doc | grep -q "状态：听懂了" || fail "这一轮该写成「听懂了」，没写成"
check "「听懂了」之后停在拍板闸门，还没往下" "听懂" "$(stage_now)"

export FAKE_WRITE=""                                  # 别再改文档
( cd "$SANDBOX" && ./loop.sh go >/dev/null 2>&1 )     # 这一次 go = 你点头
check "你点头之后才进第2步" "goal" "$(stage_now)"

# ---------- 六、轮数到顶要停，不许问个没完 ----------
S2="$TMP/sandbox2"
cp -r "$SANDBOX" "$S2"; rm -rf "$S2/.loop" "$S2/docs"
export FAKE_WRITE="$S2/docs/00-听到的.md"
export FAKE_BODY='原话：「随便说点什么」

轮次：第 3 轮   状态：还没听懂'
( cd "$S2" && LISTEN_MAX_ROUNDS=3 ./loop.sh start "随便说点什么" >/dev/null 2>&1 )
out="$( cd "$S2" && LISTEN_MAX_ROUNDS=3 ./loop.sh go 2>&1 )"
printf '%s' "$out" | grep -q "还是没聊拢" \
  && pass "问到上限会说实话，不无限问下去" \
  || fail "到了轮数上限还在若无其事地接着问"

echo
if [ "$FAILED" = 0 ]; then echo "第1步自测：全部通过"; else echo "第1步自测：有失败项"; fi
exit "$FAILED"
