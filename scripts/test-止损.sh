#!/usr/bin/env bash
# 止损（stoploss）自测。不花钱、不联网。
#
# 止损线的失败方式也是静默的：屏幕说"记下了"，.loop/止损线 却是空的。
# 日报每天拿这条对"到没到止损线"——写丢了，就等于永远不会喊停，
# 而这套系统存在的头号意义就是"该停的时候喊停"。
#
# 想亲眼看它会红：BREAK=1 bash scripts/test-止损.sh
#   会把沙盘里 state_set 的落盘掐成写到 /dev/null，止损线文件不会生成，测试必须变红。

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

# —— 故意弄坏（证明测试会红）：让 state_set 不再落盘 ——
if [ -n "${BREAK:-}" ]; then
  sed -i 's#> "\$STATE_DIR/\$key"#> /dev/null#' "$SB/scripts/lib.sh"
fi

F="$SB/.loop/止损线"
TXT="到6月底还没有10个付费用户就停，然后改方向"
run() { ( cd "$SB" && ./loop.sh "$@" ); }

echo
echo "=== 止损 stoploss 自测 ==="

# 1. 定一条止损线，文件要真出现
run 止损 "$TXT" >/dev/null 2>&1
[ -f "$F" ] && pass "定完之后 .loop/止损线 真的生成了" \
  || fail "止损线文件没生成（屏幕上可能还写着'记下了'）"

# 2. 写进去的内容要一字不差（查真实副作用）
check "止损线内容 = 原文" "$TXT" "$(cat "$F" 2>/dev/null)"

# 3. 不带参数只是"看一眼"，不许把已定的止损线覆盖/清空
run 止损 >/dev/null 2>&1
check "空参数不覆盖已定的止损线" "$TXT" "$(cat "$F" 2>/dev/null)"

echo
if [ "$FAILED" = 0 ]; then echo "止损自测：全部通过"; else echo "止损自测：有失败项"; fi
exit "$FAILED"
