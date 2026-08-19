#!/usr/bin/env bash
# 预算闸门留痕自测（验证的规矩 第 8 条）。不花钱、不联网。
#
# 这条防的不是「命令报没报错」，是【闸门被谁抬过，事后查不查得到】。
# 出处：2026-08-18 执行 AI 自己把上限从 $2 提到 $4，跑完才在汇报里如实说。
# 诚实，但顺序反了——能自己抬闸的闸门不是闸门。
# 这里不加审批（那会挡住正常使用），只查【每次改动是不是真落了一行痕迹】。
#
# 想亲眼看它会红：BREAK=1 bash scripts/test-闸门留痕.sh
#   会把沙盘里那条追加写掐成写到 /dev/null——屏幕照样说"设成了"，
#   但记录文件里什么都没有。这就是"看起来对但其实没做"。

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
SB="$TMP/sb"; mkdir -p "$SB"
cp "$REPO/loop.sh" "$SB/"
cp -r "$REPO/scripts" "$SB/"
rm -rf "$SB/scripts/__pycache__"
chmod +x "$SB/loop.sh"

# —— 故意弄坏（证明测试会红）：掐掉留痕那一次追加写 ——
# 注意注入点在【被测代码】上，不在下面任何一条期望值上。
if [ -n "${BREAK:-}" ]; then
  sed -i 's#>> "\$trail"#> /dev/null#' "$SB/loop.sh"
fi

T="$SB/.loop/闸门记录.tsv"
run() { ( cd "$SB" && ./loop.sh "$@" ); }

echo
echo "=== 预算闸门留痕自测（第 8 条） ==="

# 1. 第一次设，记录文件要真出现
run budget 5 >/dev/null 2>&1
[ -f "$T" ] && pass "设过预算之后 .loop/闸门记录.tsv 真的生成了" \
             || fail "没生成 .loop/闸门记录.tsv（屏幕说设好了，痕迹没落）"

# 2. 第一次那行要写明「没设过 → 5」
if [ -f "$T" ] && awk -F'\t' 'NR==2 && $2=="没设过" && $3=="5"{f=1} END{exit !f}' "$T"; then
  pass "第一次设，痕迹写明了「没设过 → 5」"
else
  fail "第一次那行不对（该是 没设过 → 5）"
fi

# 3. 改一次，必须再落一行；两次改动＝两行
run budget 7 >/dev/null 2>&1
n=0; [ -f "$T" ] && n="$(awk 'NR>1' "$T" | grep -c . || true)"
[ "$n" -eq 2 ] && pass "改了两次，记录里就是两行（一次一行，不覆盖）" \
                || fail "改了两次，记录里应该有 2 行，实际 $n 行"

# 4. 第二行要能看出「从 5 到 7」——查得到抬闸的幅度，而不只是"改过"
if [ -f "$T" ] && awk -F'\t' 'NR==3 && $2=="5" && $3=="7"{f=1} END{exit !f}' "$T"; then
  pass "看得出是从 \$5 抬到 \$7（幅度查得到，不只是「改过」）"
else
  fail "第二行看不出从 5 到 7"
fi

# 5. 设成同一个数也要留痕——「没变化就不记」会漏掉反复试探
run budget 7 >/dev/null 2>&1
n2=0; [ -f "$T" ] && n2="$(awk 'NR>1' "$T" | grep -c . || true)"
[ "$n2" -eq 3 ] && pass "设成同一个数也留痕（反复试探也查得到）" \
                 || fail "设成同一个数该也留一行，实际共 $n2 行"

# 6. 非法输入不许污染记录
run budget abc >/dev/null 2>&1
n3=0; [ -f "$T" ] && n3="$(awk 'NR>1' "$T" | grep -c . || true)"
[ "$n3" -eq 3 ] && pass "乱输入被挡住，没往记录里写脏行" \
                 || fail "乱输入污染了记录（该还是 3 行，实际 $n3 行）"

# 7. 闸门的值本身没被留痕这件事搞坏
v="$(cat "$SB/.loop/budget" 2>/dev/null || echo)"
[ "$v" = "7" ] && pass "留痕没影响闸门本身的值（还是 7）" \
                || fail "闸门的值坏了（该是 7，实际「$v」）"

echo
if [ "$FAILED" -eq 0 ]; then echo "闸门留痕自测：全部通过"; else echo "闸门留痕自测：有失败"; fi
exit "$FAILED"
