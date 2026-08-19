#!/usr/bin/env bash
# 开新项目要先清场 —— 自测。不花钱、不联网。
#
# 这条防的是 2026-08-19 真出过的那件事：
#   .loop/ran_giants=yes 还在、docs/ 里躺着上一个项目的文档，
#   然后你输入一个全新的想法 —— 系统认为第2、3步「已经做完了」，
#   而且 run_stage 会把那些旧文档当上下文喂给 AI。
#   屏幕上全是 ✓，底下全是别人项目的材料。
#
# 所以这里不测"start 有没有报错"，测三件真事：
#   1. 旧文档【真的】从 docs/ 里消失了（不是留在原地）
#   2. 旧的 ran_* 标记【真的】没了（否则新项目一上来就"已完成"）
#   3. 旧东西【一个都没被删】，在归档目录里找得到
#
# 还有一条容易被忽略、但破了会很烦的：
#   4. 接口钥匙不许跟着挪走 —— 换个想法不该让你重配一次钥匙
#
# 想亲眼看它会红：BREAK=1 bash scripts/test-开新项目.sh
#   会把沙盘里 start 那段清场掐掉 —— 屏幕照样说"记下了"，
#   但旧文档还在，新项目继承了上一个项目的一切。

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
SB="$TMP/sb"; mkdir -p "$SB/.loop/接口" "$SB/docs" "$SB/.claude/commands"
cp "$REPO/loop.sh" "$SB/"
cp -r "$REPO/scripts" "$SB/"
rm -rf "$SB/scripts/__pycache__"
chmod +x "$SB/loop.sh"

# —— 故意弄坏（证明测试会红）：把 start 里那段清场掐掉 ——
# 注入点落在被测代码上，不在下面任何一条期望值上。
if [ -n "${BREAK:-}" ]; then
  sed -i 's/^  if had_run; then$/  if false; then/' "$SB/loop.sh"
fi

# —— 造一个「脏」现场：上一个项目跑到一半 ——
printf '给我做一个管客户跟进的小工具\n' > "$SB/.loop/原始想法.txt"
echo edge > "$SB/.loop/stage"
echo yes  > "$SB/.loop/ran_giants"
echo yes  > "$SB/.loop/ran_goal"
echo yes  > "$SB/.loop/signoff_听懂"
printf 'ANTHROPIC_AUTH_TOKEN=不许弄丢我\n' > "$SB/.loop/接口/deepseek.key"
printf '# 01 · 巨人的肩膀\n\n上一个项目的竞品调研，跟新想法毫无关系。\n' \
  > "$SB/docs/01-巨人的肩膀.md"
printf '# 00 · 目标\n\n上一个项目的目标。\n' > "$SB/docs/00-目标.md"

# 假 claude：start 最后会调 go，别让它真去花钱
mkdir -p "$TMP/bin"
printf '#!/usr/bin/env bash\ncat >/dev/null\necho "（假 claude，什么都没干）"\n' > "$TMP/bin/claude"
chmod +x "$TMP/bin/claude"

echo
echo "=== 开新项目要先清场 自测 ==="

( cd "$SB" && CLAUDE_BIN="$TMP/bin/claude" ./loop.sh start "帮直播卖饰品的老板算订货" ) \
  > "$TMP/out.txt" 2>&1 || true

# 1. 旧文档必须从 docs/ 消失
if [ -f "$SB/docs/01-巨人的肩膀.md" ] || [ -f "$SB/docs/00-目标.md" ]; then
  fail "上一个项目的文档还留在 docs/ 里 —— 新项目会以为这几步已经做完了"
  ls "$SB/docs/"
else
  pass "上一个项目的文档从 docs/ 挪走了"
fi

# 2. 旧的 ran_* 必须没了
if [ -f "$SB/.loop/ran_giants" ] || [ -f "$SB/.loop/ran_goal" ]; then
  fail "旧的 ran_* 标记还在 —— 新想法一上来第2、3步就是「已完成」"
else
  pass "旧的完成标记清干净了"
fi

# 3. 一个都不许被删 —— 必须在归档里找得到
BAK="$(ls -d "$SB"/.loop-backup-* 2>/dev/null | head -1)"
if [ -n "$BAK" ] && [ -f "$BAK/docs/01-巨人的肩膀.md" ] && [ -f "$BAK/.loop/ran_giants" ]; then
  pass "旧东西全在归档里（$(basename "$BAK")），一个都没删"
else
  fail "归档里找不到旧东西 —— 挪走可以，删掉不行"
fi

# 4. 归档目录名要带上一个想法的头几个字，回头认得出是哪一次
case "${BAK:-}" in
  *管客户*) pass "归档名带着上一个想法，回头认得出是哪一次" ;;
  *) fail "归档名认不出是哪一次：${BAK:-（没有）}" ;;
esac

# 5. 钥匙不许跟着走
if [ -f "$SB/.loop/接口/deepseek.key" ] && grep -q '不许弄丢我' "$SB/.loop/接口/deepseek.key"; then
  pass "接口钥匙留在原处（换个想法不用重配钥匙）"
else
  fail "钥匙被一起挪走了 —— 换个想法就得重配一次，没道理"
fi

# 6. 新想法要真的记下了，而且从第一步开始
grep -q '算订货' "$SB/.loop/原始想法.txt" 2>/dev/null \
  && pass "新想法记下了" || fail "新想法没记下"
[ "$(cat "$SB/.loop/stage" 2>/dev/null)" = "听懂" ] \
  && pass "从第一步「听懂」开始，不是接着上一个项目往下走" \
  || fail "进度不对：$(cat "$SB/.loop/stage" 2>/dev/null)（该是 听懂）"

# 7. 屏幕上要说人话，让人知道发生了什么
grep -q '上一次没做完' "$TMP/out.txt" \
  && pass "屏幕上说清了「有旧东西，挪开了」" \
  || fail "清了场却不吭声 —— 人不知道自己的旧东西去哪了"

echo
if [ "$FAILED" -eq 0 ]; then echo "开新项目自测：全部通过"; else echo "开新项目自测：有失败"; fi
exit "$FAILED"
