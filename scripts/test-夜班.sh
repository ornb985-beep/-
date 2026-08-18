#!/usr/bin/env bash
# 夜班（赛马）自测。不花钱、不联网、不调真 AI。
#
# 夜班最坏的失败方式不是报错，是【它一整晚都在跑，但跑的全是同一个想法】——
# 屏幕上一样热闹，台账一样在涨，赛马悄悄退化成深挖，而老板睡着了看不见。
# 所以这里测的不是"命令报没报错"，测的是：
#   轮转公不公平 · 停下的想法还捞不捞 · 台账有没有真落 · 想法之间隔没隔开。
#
# 想亲眼看它会红：BREAK=1 bash scripts/test-夜班.sh
#   会把沙盘里挑人的规则改成"永远挑第一个"（屏幕照跑、台账照涨），
#   公平那一项必须因此变红。

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }
check() {
  if [ "$2" = "$3" ]; then pass "$1"
  else fail "$1"; printf '         期望：%s\n         实际：%s\n' "$2" "$3"; fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
SB="$TMP/sb"
mkdir -p "$SB"
cp "$REPO/loop.sh" "$SB/"
cp -r "$REPO/scripts" "$SB/"
rm -rf "$SB/scripts/__pycache__"
cp -r "$REPO/.claude" "$SB/"
cp -r "$REPO/references" "$SB/"
cp "$REPO/CLAUDE.md" "$SB/"
chmod +x "$SB/loop.sh"

# —— 故意弄坏（证明测试会红）：跑不动的想法【不标记】，于是被一捞再捞 ——
# 这是夜班最贵的失败方式：屏幕照样滚、台账照样涨、钱照样花，
# 但一整晚都在对着同一堵墙撞。注入点在被测代码上，不在期望值上。
if [ -n "${BREAK:-}" ]; then
  sed -i 's|race_set_status "$id" "等你"|:|g; s|race_set_status "$id" "卡住"|:|g' "$SB/loop.sh"
fi

# 假的 claude：什么都不做，但报一笔花销，好验账
FAKE="$TMP/bin"; mkdir -p "$FAKE"
cat > "$FAKE/claude" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
echo '{"result":"（假的）","total_cost_usd":0.10,"duration_ms":10}'
EOF
chmod +x "$FAKE/claude"

# 假的自检：默认放行。测「红了要拦住」的时候换成不放行的那把。
GREEN="$TMP/green.sh"; printf '#!/usr/bin/env bash\nexit 0\n' > "$GREEN"; chmod +x "$GREEN"
RED="$TMP/red.sh";     printf '#!/usr/bin/env bash\nexit 1\n' > "$RED";   chmod +x "$RED"

run() { ( cd "$SB" && CLAUDE_BIN="$FAKE/claude" LOOP_NIGHT_CHECK="$GREEN" ./loop.sh "$@" ); }

echo
echo "=== 夜班 赛马自测 ==="

# 1. 想法箱空的时候不许跑（不然一整晚在空转）
out="$(run 夜班 1 2>&1)"; rc=$?
[ "$rc" -ne 0 ] && pass "想法箱是空的就不跑（退出码非 0）" \
                || fail "想法箱是空的还往下跑了"

# 2. 收想法：目录、想法箱、状态都要真落地
run 想法 "甲" >/dev/null 2>&1
run 想法 "乙" >/dev/null 2>&1
run 想法 "丙" >/dev/null 2>&1
[ -d "$SB/赛马/001" ] && [ -d "$SB/赛马/003" ] \
  && pass "三个想法各有自己的地盘" || fail "想法目录没建出来"
check "想法箱里真的有三行" 3 "$(awk 'NR>1' "$SB/赛马/想法箱.tsv" | wc -l | tr -d ' ')"

# 3. 收想法这一步不许花钱（它只是排队）
[ ! -f "$SB/赛马/001/.loop/cost.tsv" ] \
  && pass "光收想法不花钱（还没有账本）" || fail "收个想法就花钱了"

# 4. 参考资料是共用的软链，不是各拷一份（拷贝会各自漂）
[ -L "$SB/赛马/001/references" ] \
  && pass "references 是软链，三个想法共用一份" || fail "references 被拷贝了，迟早各自漂"

# 5. 自检红了必须拦住——地基坏了不许生产一整晚
out="$( cd "$SB" && CLAUDE_BIN="$FAKE/claude" LOOP_NIGHT_CHECK="$RED" ./loop.sh 夜班 1 2>&1 )"; rc=$?
[ "$rc" -ne 0 ] && pass "自检红了就不开工（退出码非 0）" || fail "自检红了还照跑"
case "$out" in *自检没过*) pass "而且明说了是自检没过" ;; *) fail "没说清为什么不跑" ;; esac

# 6. 【最重要】轮转公平：三个想法，三轮，每人各一轮
run 夜班 1 >/dev/null 2>&1
uniq_ids="$(awk -F'\t' 'NR>1 {print $2}' "$SB/赛马/台账.tsv" | sort -u | wc -l | tr -d ' ')"
check "三轮跑了三个不同的想法（赛马没退化成深挖）" 3 "$uniq_ids"

# 7. 台账每跑一轮就落一行
rows="$(awk 'NR>1' "$SB/赛马/台账.tsv" | wc -l | tr -d ' ')"
[ "$rows" -ge 3 ] && pass "台账每一轮都落了一行（共 $rows 行）" \
                  || fail "台账丢账了，只有 $rows 行"

# 8. 停下来的想法不再被反复捞（不然就是对着同一堵墙撞一晚上）
before="$(awk 'NR>1' "$SB/赛马/台账.tsv" | wc -l | tr -d ' ')"
run 夜班 1 >/dev/null 2>&1
after="$(awk 'NR>1' "$SB/赛马/台账.tsv" | wc -l | tr -d ' ')"
check "全停下之后再跑，一轮都不多跑" "$before" "$after"

# 9. 想法之间要隔开：它们的文档不许落进仓库自己的 docs
[ ! -f "$SB/docs/00-听到的.md" ] \
  && pass "想法的产出没串进仓库的 docs（地盘是隔开的）" || fail "想法把东西写进了公共 docs"

# 10. 砍：状态要真的变，而且夜班不再跑它
run 砍 002 >/dev/null 2>&1
check "砍掉之后状态是淘汰" "淘汰" "$(awk -F'\t' 'NR>1 && $1=="002"{print $3}' "$SB/赛马/想法箱.tsv")"
[ -d "$SB/赛马/002" ] && pass "砍掉只是不跑了，东西还在（随时能翻）" || fail "砍掉把人家目录删了"

# 11. 留：放回跑道，而且真的会被再跑一轮
run 留 002 >/dev/null 2>&1
check "留下之后状态回到在跑" "在跑" "$(awk -F'\t' 'NR>1 && $1=="002"{print $3}' "$SB/赛马/想法箱.tsv")"
before="$(awk 'NR>1' "$SB/赛马/台账.tsv" | wc -l | tr -d ' ')"
run 夜班 1 >/dev/null 2>&1
after="$(awk 'NR>1' "$SB/赛马/台账.tsv" | wc -l | tr -d ' ')"
[ "$after" -gt "$before" ] && pass "放回去的想法今晚真的又跑了" || fail "留了但没再跑"

# 12. 战报：不许中途断，三个想法都要在
out="$(run 战报 2>&1)"; rc=$?
check "战报跑完整（退出码 0）" 0 "$rc"
n=0
for w in 001 002 003; do case "$out" in *"$w"*) n=$((n+1)) ;; esac; done
check "战报里三个想法一个不漏" 3 "$n"
case "$out" in *砍*) pass "战报告诉你早上只做一个动作：砍" ;; *) fail "战报没说该干什么" ;; esac

echo
if [ "$FAILED" -eq 0 ]; then echo "夜班自测：全部通过"; else echo "夜班自测：有失败项"; fi
exit "$FAILED"
