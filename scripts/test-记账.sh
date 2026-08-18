#!/usr/bin/env bash
# 记账（account）自测。不花钱、不联网。
#
# 记账最坏的失败方式不是报错，是【屏幕上说"记下了"，账本.tsv 里却什么都没落】。
# 日报和看板都读这个文件，一旦静默丢账，后面全是错的数，而且看不出来。
# 所以这里不测"命令报没报错"，测【.loop/账本.tsv 里到底落了什么】。
#
# 想亲眼看它会红：BREAK=1 bash scripts/test-记账.sh
#   会把沙盘里 cmd_ledger 的追加写掐成写到 /dev/null（屏幕照样说"记下了"，
#   但账本不会有那一行）——这就是"看起来对但其实没做"，测试必须因此变红。

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
chmod +x "$SB/loop.sh"

# —— 故意弄坏（证明测试会红）：把追加写掐掉，只留下屏幕上那句"记下了" ——
if [ -n "${BREAK:-}" ]; then
  sed -i 's#>> "\$LEDGER"#> /dev/null#' "$SB/loop.sh"
fi

L="$SB/.loop/账本.tsv"
run() { ( cd "$SB" && ./loop.sh "$@" ); }

echo
echo "=== 记账 account 自测 ==="

# 1. 记一笔收入，账本文件要真出现
run 记账 收 500 "第一单" >/dev/null 2>&1
[ -f "$L" ] && pass "记账之后 .loop/账本.tsv 真的生成了" \
  || fail "账本.tsv 没生成（屏幕上可能还写着'记下了'）"

# 2. 落进去的那一行，四列都要对（核心：查真实副作用，不查回显）
last="$(tail -1 "$L" 2>/dev/null)"
check "日期列 = 今天"   "$(date '+%Y-%m-%d')" "$(printf '%s' "$last" | cut -f1)"
check "收支列 = 收"     "收"                  "$(printf '%s' "$last" | cut -f2)"
check "金额列 = 500"    "500"                 "$(printf '%s' "$last" | cut -f3)"
check "说明列 = 第一单"  "第一单"              "$(printf '%s' "$last" | cut -f4)"

# 3. 表头要在（日报/看板靠列位解析，表头丢了就全错位）
check "表头第 3 列 = 金额" "金额" "$(head -1 "$L" 2>/dev/null | cut -f3)"

# 4. 再记一笔支出，必须【追加】不是【覆盖】——两条数据行都要在
run 记账 支 30 "服务器" >/dev/null 2>&1
datarows="$(($(wc -l < "$L") - 1))"
check "两笔都在（追加而非覆盖），共 2 条数据行" "2" "$datarows"
check "第二笔收支列 = 支" "支" "$(tail -1 "$L" | cut -f2)"

# 5. 非法收支类别要被拒，而且【不许静默写坏账】
rows_before="$(wc -l < "$L")"
rc=0; run 记账 增 100 >/dev/null 2>&1 || rc=$?
[ "$rc" -ne 0 ] && pass "非法类别（增）被拒，退出码非零" \
  || fail "非法类别没被拒（静默接受了坏数据）"
check "非法类别没污染账本（行数没变）" "$rows_before" "$(wc -l < "$L")"

echo
if [ "$FAILED" = 0 ]; then echo "记账自测：全部通过"; else echo "记账自测：有失败项"; fi
exit "$FAILED"
