#!/usr/bin/env bash
# 数字漂移测试：工程交接包.md 里写死的「命令数」是个断言，
# 必须和 loop.sh 真实数出来的一致。改了命令没同步改文档，这里就会红。
#
# 照 test-听懂.sh 里"说明书第N步 vs 真实位置"那套逐项比对的路子。
# 只守【命令数】——它是断言。自测子项数 55 标了"快照"（快照本来就允许过期），不进这里。
# 尺子用第八节那条新的（含 A-Z0-9-、并排除 help），别用旧的，否则又会漂。
#
# 想亲眼看它会红：BREAK=1 bash scripts/test-数字漂移.sh
#   会读一份被改成 45 的临时文档副本，证明不一致时确实变红。

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; }

DOC="$REPO/工程交接包.md"
if [ -n "${BREAK:-}" ]; then
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  cp "$DOC" "$TMP/doc.md"
  sed -i 's/主程序，46 条命令/主程序，45 条命令/' "$TMP/doc.md"
  DOC="$TMP/doc.md"
fi

echo
echo "=== 数字漂移：命令数（文档断言 vs loop.sh 实数） ==="

# 文档里写死的命令数（认第三节"主程序，N 条命令"那个权威位置）
doc_n="$(grep -oE '主程序，[0-9]+ 条命令' "$DOC" | head -1 | grep -oE '[0-9]+' || true)"
# loop.sh 真实数出来的（第八节那条新尺子：含 A-Z0-9-，且排除 help）
real_n="$(sed -n '/^main() {/,/^}/p' "$REPO/loop.sh" | grep -E '^\s+[a-zA-Z0-9|一-龥-]+\)' | grep -cv help || true)"

if [ -z "$doc_n" ]; then
  fail "文档里没找到「主程序，N 条命令」这个断言——格式被改了？"
  FAILED=1
elif [ "$doc_n" = "$real_n" ]; then
  pass "命令数一致：文档写 $doc_n，loop.sh 实数 $real_n"
else
  fail "命令数漂了：文档写 $doc_n，loop.sh 实数 $real_n。改了命令就得同步改文档那个数。"
  FAILED=1
fi

echo
if [ "$FAILED" = 0 ]; then echo "数字漂移自测：全部通过"; else echo "数字漂移自测：有失败项"; fi
exit "$FAILED"
