#!/usr/bin/env bash
# 产品蓝图收敛循环的自测。不花钱、不联网。
#
# 这个循环最坏的失败方式：
#   ① 它自己说"定了"就往下走了 —— 拍板必须是你亲口说的，不是它替你说
#   ② 你说"挺好的"被当成拍板 —— 那是客气，不是决定
#   ③ 一次把好几个问题甩给你（用户只做一件事：回答一个问题）
#   ④ 每答一个就重跑一次 AI（三个问题花三次钱）
#   ⑤ 改了十几轮还在原地转，不说实话

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }

echo
echo "=== 蓝图收敛循环自测 ==="

TMP="$(mktemp -d)"
if [ "${KEEP_TMP:-0}" = 1 ]; then echo "沙盘留在：$TMP"; else trap 'rm -rf "$TMP"' EXIT; fi
SB="$TMP/sb"; mkdir -p "$SB/docs"
cp "$REPO/loop.sh" "$SB/"
cp -r "$REPO/scripts" "$REPO/.claude" "$REPO/roles-模板" "$SB/"
rm -rf "$SB/scripts/__pycache__"
chmod +x "$SB/loop.sh"
printf '# 听到的\n真实痛点：老忘了回访\n' > "$SB/docs/00-听到的.md"

mkdir -p "$TMP/bin"
cat > "$TMP/bin/claude" <<'FAKE'
#!/usr/bin/env bash
p="$(cat)"
n=$(ls "$DUMP_DIR" 2>/dev/null | wc -l)
printf '%s' "$p" > "$DUMP_DIR/$n.txt"
[ -n "${FAKE_WRITE:-}" ] && { mkdir -p "$(dirname "$FAKE_WRITE")"; printf '%s\n' "${FAKE_BODY:-}" > "$FAKE_WRITE"; }
echo '{"result":"假的","total_cost_usd":0.01,"duration_ms":100}'
FAKE
chmod +x "$TMP/bin/claude"
export CLAUDE_BIN="$TMP/bin/claude" DUMP_DIR="$TMP/dump"; mkdir -p "$DUMP_DIR"
export FAKE_WRITE="$SB/docs/00-蓝图.md"
export FAKE_BODY='# 00 · 蓝图

轮次：第 1 轮   状态：还在改

## 你要做的这个东西
一个不让你把老客户搞丢的小本子

## 我想确认一件事

### 问题 1：甲问题
- **A** 甲的A
- **B** 甲的B

### 问题 2：乙问题
- **A** 乙的A

## 详细版
### 用户流程
一二三'

cd "$SB"
out="$(./loop.sh 蓝图 2>&1)"

# ---------- 一、还没定，不许往下走 ----------
printf '%s' "$out" | grep -q "有一件事想跟你确认" \
  && pass "画完停下来问你，没有自己往下跑" || fail "没停下来"

# ---------- 二、一次只给一个 ----------
if printf '%s' "$out" | grep -q "甲问题" && ! printf '%s' "$out" | grep -q "乙问题"; then
  pass "一次只显示一个问题"
else
  fail "一次把两个问题都甩出来了"
fi

# ---------- 三、详细版不许倒给用户 ----------
printf '%s' "$out" | grep -q "用户流程" \
  && fail "把详细版也倒到屏幕上了 —— 默认只该给人性化那版" \
  || pass "屏幕上只给人性化那版，详细版留在文件里"

# ---------- 四、答第一个：本地接上第二个，不重跑 AI ----------
before=$(ls "$DUMP_DIR" | wc -l)
out2="$(./loop.sh 改 "A" 2>&1)"
after=$(ls "$DUMP_DIR" | wc -l)
printf '%s' "$out2" | grep -q "乙问题" \
  && pass "答完第一个，本地接上第二个" || fail "没接上第二个"
[ "$after" -eq "$before" ] \
  && pass "问第二个没有再花钱跑 AI" || fail "每答一个就重跑一次 AI"

# ---------- 五、全答完才重跑一轮 ----------
export FAKE_BODY='# 00 · 蓝图

轮次：第 2 轮   状态：还在改

## 我想确认一件事

### 问题 1：第二轮的问题
- **A** 是

## 详细版'
out3="$(./loop.sh 改 "A" 2>&1)"
[ "$(grep -cE '轮次(:|：)[[:space:]]*第[[:space:]]*2' docs/00-蓝图.md)" -ge 1 ] \
  && pass "全答完了才重跑一轮（轮次前进）" || fail "没有重跑"

# ---------- 六、【最要紧】它不许自己说定了 ----------
grep -qE '状态(:|：)[[:space:]]*就是它了' docs/00-蓝图.md \
  && fail "它自己写了「就是它了」——拍板必须是你亲口说的" \
  || pass "它没替你拍板"

# ---------- 七、你亲口说了，才锁 ----------
out4="$(./loop.sh 定了 2>&1)"
printf '%s' "$out4" | grep -q "定了" && grep -qE '状态(:|：)[[:space:]]*就是它了' docs/00-蓝图.md \
  && pass "你说「定了」之后才锁定" || fail "锁定没生效"
grep -q "对，这就是我要做的" docs/00-蓝图.md \
  && pass "拍板这件事留了痕（回头查得到是谁定的）" || fail "拍板没留痕"

# ---------- 八、锁了之后再跑，是「定了」不是接着问 ----------
export FAKE_BODY='轮次：第 3 轮   状态：就是它了'
out5="$(./loop.sh 蓝图 2>&1)"
printf '%s' "$out5" | grep -q "接着往下" \
  && pass "锁定之后提示往下走，不再纠缠" || fail "锁定后还在问"

# ---------- 九、转太多轮要说实话 ----------
SB2="$TMP/sb2"; cp -r "$SB" "$SB2"; rm -rf "$SB2/.loop"
export FAKE_WRITE="$SB2/docs/00-蓝图.md"
printf '轮次：第 12 轮   状态：还在改\n' > "$SB2/docs/00-蓝图.md"
out6="$( cd "$SB2" && BP_MAX_ROUNDS=12 ./loop.sh 蓝图 2>&1 )"
printf '%s' "$out6" | grep -q "还没定下来" \
  && pass "转太多轮会说实话，不无限转下去" || fail "转了十几轮还在若无其事地接着问"

# ---------- 十、知识库那个口子真的会被读进去 ----------
SB3="$TMP/sb3"; cp -r "$SB" "$SB3"; rm -rf "$SB3/.loop" "$SB3/docs/00-蓝图.md"
mkdir -p "$SB3/references/我的知识库"
printf '我的审美：宁可少一个功能，也不要多一次点击\n' > "$SB3/references/我的知识库/审美.md"
export FAKE_WRITE="" DUMP_DIR="$TMP/dump3"; mkdir -p "$DUMP_DIR"
( cd "$SB3" && ./loop.sh 蓝图 >/dev/null 2>&1 )
grep -rq "宁可少一个功能" "$DUMP_DIR" 2>/dev/null \
  && pass "references/我的知识库/ 里的东西真的喂进去了" \
  || fail "知识库那个口子是空的 —— 放了东西也没被读"

echo
if [ "$FAILED" = 0 ]; then echo "蓝图自测：全部通过"; else echo "蓝图自测：有失败项"; fi
exit "$FAILED"
