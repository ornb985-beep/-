#!/usr/bin/env bash
# 信号翻译表同步自测。不花钱、不联网。
#
# 为什么要有这条：
# .claude/commands/听懂.md 里的「信号翻译表」是从 references/人性档案.md
# 抄过去的——抄，是因为第 1 步那三条省钱硬规矩不许它去读 references/。
# 代价是【同一份内容有了两个真身】：档案改了，听懂里那份不会跟着改，
# 而且没有人会发现。这个项目栽过好几次这种漂移（九步编号手写在 20 个文件里）。
#
# 所以这条尺子只干一件事：听懂里那张表的每一行「听到」什么，
# 必须在人性档案里找得到。找不到就红。
#
# 想亲眼看它会红：BREAK=1 bash scripts/test-翻译表同步.sh
#   会把沙盘里【人性档案】的一行改掉（模拟档案更新了、听懂没跟上）。

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
CMD="$TMP/听懂.md"; DOC="$TMP/人性档案.md"
cp "$REPO/.claude/commands/听懂.md" "$CMD"
cp "$REPO/references/人性档案.md"   "$DOC"

# —— 故意弄坏（证明测试会红）：档案那边改了，听懂那边没跟上 ——
# 注入点落在【被比对的档案】上，不是落在期望值上。
if [ -n "${BREAK:-}" ]; then
  sed -i 's/「想明白再说」/「等我再看看」/; s/"想明白再说"/"等我再看看"/' "$DOC"
fi

echo
echo "=== 信号翻译表同步（听懂 抄的那份 vs 人性档案 原件） ==="

# 只取「怎么读」那一节里的表，别把听懂里别的表（铁律表、判错表）一起扫进来。
# 取第一列「听到」。
#
# 【不许用 grep 的 [^」] 这种否定字符类】：这台机器的 grep 按【字节】走，
# 「」的字节会跟别的汉字撞车（「想明白再说」的「再」、「什么」的「什」里
# 就带着同样的字节），结果是【静悄悄地少抽几行】——尺子自己犯了
# "看起来对但其实没做"。所以按 | 切列，去尖括号用 sed。
signals="$(awk '/^### 怎么读/{on=1;next} on&&/^###/{exit} on&&/^\|/' "$CMD" \
  | awk -F'|' '{print $2}' \
  | sed 's/^ *//; s/ *$//; s/「//g; s/」//g' \
  | grep -v '^听到$' | grep -vE '^-*$' | grep -v '^$')"
n="$(printf '%s\n' "$signals" | grep -c . || true)"

[ "$n" -ge 5 ] && pass "从听懂里取到了 $n 条信号（尺子扫到东西了，不是扫空报绿）" \
                || fail "只从听懂里取到 $n 条信号，尺子可能对不上表格式了"

miss=0
while IFS= read -r sig; do
  [ -n "$sig" ] || continue
  if ! grep -qF "$sig" "$DOC"; then
    fail "「$sig」在听懂里有，人性档案里找不到 —— 两份真身漂了"
    miss=1
  fi
done <<< "$signals"
[ "$miss" -eq 0 ] && pass "听懂里每一条信号，人性档案里都找得到（没漂）"

# 档案那边也得还在，别哪天档案被删了这条测试还一路绿
grep -q "信号翻译表" "$DOC" \
  && pass "人性档案里那张原表还在（这条测试守的是它，不是自己发明的）" \
  || fail "人性档案里找不到「信号翻译表」—— 那这条测试守的是什么？"

echo
if [ "$FAILED" -eq 0 ]; then echo "翻译表同步自测：全部通过"; else echo "翻译表同步自测：有失败"; fi
exit "$FAILED"
