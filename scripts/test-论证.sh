#!/usr/bin/env bash
# 论证（十个专家把「这事到底成不成」查一遍）的自测。不花钱、不联网。
#
# 这条命令最坏的失败方式还是那三种"看起来对"：
#   ① 专家跑了但没交东西，却被记成成功 → 汇总里是十份空气
#   ② 后跑的六个人【看不见】先跑的四个人查回来的数据
#      → 那就退化成"十个人各说各的"，这条命令的全部设计就白费了
#   ③ 预算中途用完，重跑时从头再来一遍，把已经交过的又跑一次（白烧钱）
# 这里三条都测。

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }

echo
echo "=== 论证自测 ==="

# ---------- 零、角色到底收没收到自己的身份和问题 ----------
# 这条单独排在最前面，因为它栽过：
# strip_frontmatter 对「没有 frontmatter 的文件」只输出了第一行，
# 于是每个角色收到的只有「层：参谋」这一行——身份没收到，问题也没收到。
# 它照样会输出东西（后面附着文档就能编出个样子），从外面完全看不出来。
sfp="$(mktemp)"
printf '层：参谋\n一句话：管钱的\n\n你是财务专家。\n\n---- 现在问你这件事 ----\n算这笔账\n' > "$sfp"
got="$(bash -c '. "$1/scripts/lib.sh"; strip_frontmatter "$2"' _ "$REPO" "$sfp")"
if printf '%s' "$got" | grep -q "算这笔账" && printf '%s' "$got" | grep -q "你是财务专家"; then
  pass "没有 frontmatter 的提示词，角色定义和问题都完整送到了"
else
  fail "角色收不到自己的身份/问题（strip_frontmatter 把内容吃掉了）"
  printf '         它实际收到的是：\n'; printf '%s\n' "$got" | sed 's/^/           /'
fi
sfp2="$(mktemp)"
printf -- '---\ndescription: x\n---\n\n正文\n' > "$sfp2"
got2="$(bash -c '. "$1/scripts/lib.sh"; strip_frontmatter "$2"' _ "$REPO" "$sfp2")"
printf '%s' "$got2" | grep -q "description" \
  && fail "有 frontmatter 的没被去掉（--- 开头会被当成命令行选项）" \
  || pass "有 frontmatter 的照样去得干净"
rm -f "$sfp" "$sfp2"

# 想留着沙盘自己翻：KEEP_TMP=1 bash scripts/test-论证.sh
TMP="$(mktemp -d)"
if [ "${KEEP_TMP:-0}" = 1 ]; then echo "沙盘留在：$TMP"; else trap 'rm -rf "$TMP"' EXIT; fi
SB="$TMP/sb"; mkdir -p "$SB"
cp "$REPO/loop.sh" "$SB/"
cp -r "$REPO/scripts" "$REPO/.claude" "$REPO/roles-模板" "$SB/"
rm -rf "$SB/scripts/__pycache__"
chmod +x "$SB/loop.sh"
mkdir -p "$SB/docs"
printf '# 目标\n每月净赚 2 万\n' > "$SB/docs/00-目标.md"
printf '# 听到的\n真实痛点：老忘了回访\n' > "$SB/docs/00-听到的.md"

# 假 claude：把收到的【完整提示词】存一份（用来验证上下文有没有真传过去），
# 再按 FAKE_WRITE 写出产物。
mkdir -p "$TMP/bin"
cat > "$TMP/bin/claude" <<'FAKE'
#!/usr/bin/env bash
prompt="$(cat)"
n=$(ls "$DUMP_DIR" 2>/dev/null | wc -l)
printf '%s' "$prompt" > "$DUMP_DIR/$n.txt"
if [ -n "${FAKE_WRITE:-}" ]; then
  mkdir -p "$(dirname "$FAKE_WRITE")"
  printf '%s\n' "${FAKE_BODY:-x}" > "$FAKE_WRITE"
fi
echo '{"result":"假的","total_cost_usd":0.01,"duration_ms":100}'
FAKE
chmod +x "$TMP/bin/claude"
export CLAUDE_BIN="$TMP/bin/claude"
export DUMP_DIR="$TMP/dump"; mkdir -p "$DUMP_DIR"

cd "$SB"

# ---------- 一、人不齐要拦住 ----------
out="$(./loop.sh 论证 2>&1)"
printf '%s' "$out" | grep -q "论证团还差人" \
  && pass "人不齐时拦住了，并给出招人命令" || fail "人不齐居然还往下跑"

./loop.sh hire 行研 增长 竞品 技术 财务 战略 产品 合规 运营 风控 >/dev/null 2>&1

# ---------- 二、没设预算要拦住 ----------
out="$(./loop.sh 论证 2>&1)"
printf '%s' "$out" | grep -q "先设个上限" \
  && pass "没设预算时拦住了（这是最贵的一步）" || fail "没设预算就敢跑十几次调用"

./loop.sh budget 30 >/dev/null 2>&1

# ---------- 三、跑一遍：每个人都要交东西 ----------
# 让假 claude 每次都往「当前该写的那个文件」写。用一个包装脚本按调用顺序决定写哪儿。
cat > "$TMP/bin/claude" <<'FAKE'
#!/usr/bin/env bash
prompt="$(cat)"
n=$(ls "$DUMP_DIR" | wc -l)
printf '%s' "$prompt" > "$DUMP_DIR/$n.txt"
# 从提示词里认出这是谁的活：找 work/<名字>/论证.md
target="$(printf '%s' "$prompt" | grep -oE 'work/[^/ ]+/论证\.md' | head -1)"
if [ -n "$target" ]; then
  mkdir -p "$(dirname "$SB_ROOT/$target")"
  printf '## 结论\n%s 查到的数字是 42\n' "$(basename "$(dirname "$target")")" > "$SB_ROOT/$target"
# 注意顺序：综合那一次的【上下文里】也带着 00-论证.md，里面有"作业单"三个字。
# 先判"作业单"的话，综合会被当成出作业单，把文件覆盖掉。
elif printf '%s' "$prompt" | grep -q "十个专家的意见都交上来了"; then
  cat >> "$SB_ROOT/docs/00-论证.md" <<'EOD'

## 给你的一页纸

**一句话结论**：能做，但获客是死穴

**可行性 80%**（已验证 8 条 / 承重条件共 10 条）　判定：动态型

## 承重条件核对表
| # | 条件 | 状态 |
EOD
elif printf '%s' "$prompt" | grep -q "把「这事到底成不成」拆成十个"; then
  mkdir -p "$SB_ROOT/docs"
  printf '# 00 · 论证\n论证状态：作业单已出\n\n## 二、作业单\n' > "$SB_ROOT/docs/00-论证.md"
fi
echo '{"result":"假的","total_cost_usd":0.01,"duration_ms":100}'
FAKE
chmod +x "$TMP/bin/claude"
export SB_ROOT="$SB"

out="$(./loop.sh 论证 2>&1)"

allin=1
for who in 行研 增长 竞品 技术 财务 战略 产品 合规 运营 风控; do
  [ -f "$SB/work/$who/论证.md" ] || { allin=0; echo "         $who 没交"; }
done
[ "$allin" = 1 ] && pass "十个人都交了产物" || fail "有人没交产物"

# ---------- 四、【最关键】后跑的人必须看得见先跑的人查到的数据 ----------
# 找到「财务」那次调用的提示词，看里面有没有「行研」的产物内容
judge_dump=""
for f in "$DUMP_DIR"/*.txt; do
  if grep -q "work/财务/论证.md" "$f" 2>/dev/null; then judge_dump="$f"; break; fi
done
if [ -z "$judge_dump" ]; then
  fail "找不到财务那次调用的记录"
else
  if grep -q "行研 查到的数字是 42" "$judge_dump"; then
    pass "后跑的人真的看得见先跑的人查回来的数据（这条是这条命令的命）"
  else
    fail "后跑的人看不见先跑的数据 —— 那就退化成十个人各说各的了"
  fi
fi

# ---------- 五、一页纸要摘出来打在屏幕上 ----------
printf '%s' "$out" | grep -q "一句话结论" \
  && pass "一页纸摘出来打在屏幕上了（不用翻文件）" || fail "一页纸没打出来"
printf '%s' "$out" | grep -q "承重条件核对表" \
  && fail "把完整版也一起倒给用户了 —— 一页纸就该只有一页" \
  || pass "只给了一页纸，完整版留在文件里"

# ---------- 六、可重跑：已经交过的要跳过，不许白烧钱 ----------
before=$(ls "$DUMP_DIR" | wc -l)
out2="$(./loop.sh 论证 2>&1)"
after=$(ls "$DUMP_DIR" | wc -l)
printf '%s' "$out2" | grep -q "已经交过了，跳过" \
  && pass "重跑时跳过已交的人（预算中途用完能接着跑）" || fail "重跑把已经交过的又跑了一遍"
# 只该重跑「综合」那一次
[ "$((after-before))" -le 2 ] \
  && pass "重跑只补跑了没做的（多花 $((after-before)) 次调用）" \
  || fail "重跑多花了 $((after-before)) 次调用，等于从头再来"

# ---------- 七、没交东西不许记成成功 ----------
rm -f "$SB/work/风控/论证.md"
cat > "$TMP/bin/claude" <<'FAKE'
#!/usr/bin/env bash
cat > /dev/null
echo '{"result":"我啥也没写","total_cost_usd":0.01,"duration_ms":100}'
FAKE
chmod +x "$TMP/bin/claude"
out3="$(./loop.sh 论证 2>&1)"
printf '%s' "$out3" | grep -q "风控 没交东西" \
  && pass "跑完没产出，如实记成「没交东西」" || fail "没产出却报了成功"

echo
if [ "$FAILED" = 0 ]; then echo "论证自测：全部通过"; else echo "论证自测：有失败项"; fi
exit "$FAILED"
